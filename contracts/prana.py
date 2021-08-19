from contracts.FA2 import FA2_config, FA2_core, Token_id_set
import smartpy as sp

FA2 = sp.import_template("FA2.py")

# FA2 = sp.import_template("FA2.py")
# class FA2_nft(FA2.FA2):
#     def __init__(self, config, admin):
#         FA2.FA2.__init__(self, config, admin)
#         self.config.non_fungible = True
# class prana(FA2_nft):
#     def __init__(self, config, admin):
#         super().__init__(config, admin)

class Prana(FA2):
    def __init__(self, config, admin):
        FA2.FA2.__init__(self, config, admin)
        #setting the contract to be non-fungible
        #self.config.non_fungible = True
        FA2_config(non_fungible = True, add_mutez_transfer = True)

        #initializing all the data types

        # The book Record (structure equivalent)
        self.bookInfo = sp.TRecord(encryptedBookDataHash = sp.TString,
                        unEncryptedBookDetailsCID = sp.TString,
                        publisherAddress = sp.TAddress,
                        bookPrice = sp.TNat,
                        transactionCut = sp.TNat,
                        bookSales = sp.TNat)
        
        # big_map for booksInfo
        # ISBN is the key, its corresponding details is the value
        self.booksInfo = sp.big_map(tkey = sp.TNat, tvalue = self.bookInfo)


        # The TokenDetails Record
        self.tokenDetails = sp.TRecord(isbn = sp.TNat,
                            copyNumber = sp.TNat,
                            resalePrice = sp.TNat,
                            isUpForResale = sp.TBool,
                            rentingPrice = sp.TNat,
                            isUpForRenting = sp.TBool,
                            rentee = sp.TAddress,
                            rentedAtTime = sp.TTimestamp)
        
        
        # READ READ READ READ READ READ READ READ READ READ 
        # The time period of renting is assumed to be a constant, rentingPeriod, in minutes
        self.rentingPeriod = 10


        # tokenId to TokenDetails big_map
        self.tokenData = sp.big_map(tkey = sp.TNat, tvalue = self.tokenDetails)


        # The big_map for holding all the list of rented tokens, for each address
        self.rentedTokensOfEach = sp.list(t = sp.TNat)
        self.rentedTokens = sp.big_map(tkey = sp.TAddress, tvalue = self.rentedTokensOfEach)

        # List of tokens up for resale. Don't need a big_map here.
        self.upForResaleTokens = sp.set(t = sp.TNat)

        # List of tokens up for renting. Don't need a big_map here either.
        self.upForRentingTokens = sp.set(t = sp.TNat)

        # A big_map of tokenOwners. Key is token_id, value is tokenOwner
        self.ownerOf = sp.big_map(tkey = sp.TNat, tvalue = sp.TAddress)
    
    
    # function that would take in the parameters and publish the book on blockchain
    @sp.entry_point
    def publishBook(self, params):
        sp.verify(self.bookInfo[params.isbn].publisherAddress == sp.TAddress(0))  # might need to double-check it.
        self.bookInfo[params.isbn].encryptedBookDataHash = params.encryptedBookDataHash
        self.bookInfo[params.isbn].unEncryptedBookDetailsCID = params.unEncryptedBookDetailsCID
        self.bookInfo[params.isbn].publisherAddress = params.publisherAddress
        self.bookInfo[params.isbn].bookPrice = params.bookPrice
        self.bookInfo[params.isbn].transactionCut = params.transactionCut
        self.bookInfo[params.isbn].bookSales = params.bookSales

    
    # primary purchase. Where a token will be minted.
    @sp.entry_point
    def directPurchase(self, params):
        sp.verify(self.bookInfo[params.isbn].publisherAddress != sp.TAddress(0))
        sp.verify(sp.amount >= self.bookInfo[params.isbn].bookPrice)  # assuming it's sp.amount. TODO: Double-check.
        FA2.mint(self, params)  # this must be be wrong too
        self.ownerOf[params.token_id] = sp.sender
        self.bookInfo[params.isbn].bookSales += 1
        self.tokenData[params.token_id].isbn = params.isbn
        self.tokenData[params.token_id].copyNumber = self.bookInfo[params.isbn].bookSales
        self.tokenData[params.token_id].rentee = sp.address(0)
        self.tokenData[params.token_id].rentedAtTime = 0
        sp.send(self.bookInfo[params.isbn].publisherAddress, sp.amount)


        # const contract = Sp.contract<TUnit>("tz1..." as TAddress).openSome("Invalid contract")
        # Sp.transfer(Sp.unit, 0, contract)


    # put the already purchased token for sale, by the tokenOwner

    @sp.entry_point
    def putTokenForSale(self, params):
        sp.verify(self.data.ledger[(sp.sender, params.token_id)], message = "Not authorized") #this check could be wrong.
        sp.verify(self.tokenData[params.token_id].isUpForRenting == False, message = "Can't put for sale while on rent")
        sp.verify(params.resalePrice > 0) # a greater-than-zero price is required.
        # Checks whether 10 minutes have passed since the book has been rented by someone
        sp.verify(sp.now > self.tokenData[params.token_id].rentedAtTime.add_minutes(self.rentingPeriod))
        self.tokenData[params.token_id].resalePrice = params.resalePrice
        self.tokenData[params.token_id].isUpForResale = True
        self.upForResaleTokens.add(params.token_id)


    # buy a token that's put for sale by the owner
    @sp.entry_point
    def buyToken(self, params):
        sp.verify(self.tokenData[params.token_id].isUpForResale == True, message = "Not for sale")
        sp.verify(sp.amount >= self.tokenData[params.token_id].resalePrice)
        # transactioncuts need to be distributed here
        concrete_transactionCut = sp.amount*(self.bookInfo[self.tokenData[params.token_id].isbn].transactionCut/100)
        sp.send(self.bookInfo[self.tokenData[params.token_id].isbn].publisherAddress, concrete_transactionCut)
        sp.send(self.ownerOf[params.token_id], (sp.amount - concrete_transactionCut))
        FA2_core.transfer(self, params)
        self.ownerOf[params.token_id] =  sp.sender
        self.upForResaleTokens.remove(params.tokens_id)

    # function to put a token for renting.
    @sp.entry_point
    def putForRent(self, params):
        sp.verify(self.ownerOf[params.token_id] == sp.sender, message =  "You're not the token owner")
        sp.verify(self.tokenData[params.token_id].isUpForResale == False, message = "Can't put for rent if it's on sale now")
        if self.tokenData[params.token_id].rentee != sp.address(0):
            sp.verify(sp.now > self.tokenData[params.token_id].rentedAtTime.add_minutes(self.rentingPeriod))
        self.tokenData[params.token_id].rentingPrice = params.newPrice
        self.tokenData[params.token_id].isUpForRenting = True
        self.tokenData[params.token_id].rentee = sp.address(0)
        self.upForRentingTokens.add(params.token_id)

    
    # function to rent a token
    @sp.entry_point
    def rentToken(self, params):
        sp.verify(self.tokenData[params.token_id].isUpForRenting == True, message="Hasn't been put for renting")
        sp.verify(self.tokenData[params.token_id].rentee == sp.address(0), message = "Rented by someone already.")
        sp.verify(sp.amount > self.tokenData[params.token_id].rentingPrice, message="not enough money")
        sp.verify(self.ownerOf[params.token_id] != sp.sender, message="owner can't rent own token")
        # given everyone their dues
        concrete_transactionCut = sp.amount*(self.bookInfo[self.tokenData[params.token_id].isbn].transactionCut/100)
        sp.send(self.bookInfo[self.tokenData[params.token_id].isbn].publisherAddress, concrete_transactionCut)
        sp.send(self.ownerOf[params.token_id], (sp.amount - concrete_transactionCut))
        self.tokenData[params.token_id].rentee = sp.sender
        self.tokenData[params.token_id].rentedAtTime = sp.now
        self.upForRentingTokens.remove(params.token_id)
    
    # function to consume the content, i.e actually read the book
    @sp.offchain_view(pure = True)
    def consumeContent(self, params):
        sp.verify(self.ownerOf[params.token_id] == sp.sender or self.tokenData[params.token_id].rentee == sp.sender, message="You're not authorized to view the content")
        if self.ownerOf[params.token_id] == sp.sender :
            if self.tokenData[params.token_id].rentee != sp.address(0):
                sp.verify(sp.now > self.tokenData[params.token_id].rentedAtTime.add_minutes(self.rentingPeriod))
        elif self.tokenData[params.token_id].rentee == sp.sender:
            sp.verify(sp.now < self.tokenData[params.token_id].rentedAtTime.add_minutes(self.rentingPeriod))
        return sp.string(self.bookInfo[self.tokenData[params.token_id].isbn].unEncryptedBookDetailsCID)

    