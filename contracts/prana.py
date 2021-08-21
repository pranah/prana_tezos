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
        self.rentingPeriod = sp.TNat(10)

        # incrementing token_ids to be passed in for minting
        self.enumerable_token_id = sp.TNat(1)


        # tokenId to TokenDetails big_map
        self.tokenData = sp.big_map(tkey = sp.TNat, tvalue = self.tokenDetails)


        # The big_map for holding all the list of rented tokens, for each address
        self.rentedTokensOfEach = sp.set(t = sp.TNat)
        self.rentedTokens = sp.big_map(tkey = sp.TAddress, tvalue = self.rentedTokensOfEach)

        #List of books that's been published. Don't need to remove anything once it's added
        self.publishedBooks = sp.list(t = sp.TNat)
        
        # Dynamic Set of tokens up for resale. Don't need a big_map here.
        self.upForResaleTokens = sp.set(t = sp.TNat)

        # Dynamic Set of tokens up for renting. Don't need a big_map here either.
        self.upForRentingTokens = sp.set(t = sp.TNat)

        # A big_map of tokenOwners. Key is token_id, value is tokenOwner
        self.ownerOf = sp.big_map(tkey = sp.TNat, tvalue = sp.TAddress)
    
    
    # function that would take in the parameters and publish the book on blockchain
    @sp.entry_point
    def publishBook(self, params):
        sp.verify(self.bookInfo[params.isbn].publisherAddress == sp.TAddress(0))  # might need to double-check it.
        sp.verify(params.transactionCut < 100, message = "Can't take all the money")
        self.bookInfo[params.isbn].encryptedBookDataHash = params.encryptedBookDataHash
        self.bookInfo[params.isbn].unEncryptedBookDetailsCID = params.unEncryptedBookDetailsCID
        self.bookInfo[params.isbn].publisherAddress = sp.sender
        self.bookInfo[params.isbn].bookPrice = params.bookPrice
        self.bookInfo[params.isbn].transactionCut = params.transactionCut
        self.bookInfo[params.isbn].bookSales = params.bookSales
        self.publishedBooks.add(params.isbn)

    
    # primary purchase. Where a token will be minted.
    @sp.entry_point
    def directPurchase(self, params):
        sp.verify(self.bookInfo[params.isbn].publisherAddress != sp.TAddress(0))
        sp.verify(sp.amount >= self.bookInfo[params.isbn].bookPrice)  # assuming it's sp.amount. TODO: Double-check.
        # this params would need tokenOwner from pranaHelper passed in as well.
        token_Id = self.enumerable_token_id + 1
        # parameters = (params.isbn, params.tokenOwner)  # this needs to be worked upon
        FA2.mint(address = params.tokenOwner, amount = 1, metadata = "Empty", token_id = token_Id)  # this params has got token_id, the owner's address, and amount=1 as parameters
        self.ownerOf[token_Id] = params.tokenOwner  
        self.bookInfo[params.isbn].bookSales += 1
        self.tokenData[token_Id].isbn = params.isbn
        self.tokenData[token_Id].copyNumber = self.bookInfo[params.isbn].bookSales
        self.tokenData[token_Id].rentee = sp.address(0)
        self.tokenData[token_Id].rentedAtTime = 0
        sp.send(self.bookInfo[params.isbn].publisherAddress, sp.amount)


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
        # the new tokenOwner is the tokenBuyer, passed on from pranaHelper
        FA2_core.transfer(self, params) 
        self.ownerOf[params.token_id] =  params.tokenBuyer
        self.upForResaleTokens.remove(params.tokens_id)

    # function to put a token for renting.
    @sp.entry_point
    def putForRent(self, params):
        sp.verify(self.ownerOf[params.token_id] == sp.sender, message =  "You're not the token owner")
        sp.verify(self.tokenData[params.token_id].isUpForResale == False, message = "Can't put for rent if it's on sale now")
        sp.if self.tokenData[params.token_id].rentee != sp.address(0):
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
        # give everyone their dues
        concrete_transactionCut = sp.amount*(self.bookInfo[self.tokenData[params.token_id].isbn].transactionCut/100)
        sp.send(self.bookInfo[self.tokenData[params.token_id].isbn].publisherAddress, concrete_transactionCut)
        sp.send(self.ownerOf[params.token_id], (sp.amount - concrete_transactionCut))
        self.tokenData[params.token_id].rentee = sp.sender
        self.tokenData[params.token_id].rentedAtTime = sp.now
        self.upForRentingTokens.remove(params.token_id)
        self.rentedTokensOfEach[sp.sender].add(params.token_id)
    
    # function to consume the content, i.e actually read the book
    @sp.offchain_view(pure = True)
    def consumeContent(self, params):
        sp.verify(self.ownerOf[params.token_id] == sp.sender or self.tokenData[params.token_id].rentee == sp.sender, message="You're not authorized to view the content")
        sp.if self.ownerOf[params.token_id] == sp.sender :
            sp.if self.tokenData[params.token_id].rentee != sp.address(0):
                sp.verify(sp.now > self.tokenData[params.token_id].rentedAtTime.add_minutes(self.rentingPeriod))
        sp.if self.tokenData[params.token_id].rentee == sp.sender:
            sp.verify(sp.now < self.tokenData[params.token_id].rentedAtTime.add_minutes(self.rentingPeriod))
        return sp.string(self.bookInfo[self.tokenData[params.token_id].isbn].unEncryptedBookDetailsCID)

     
    
    # view token details for backend stuff
    # returns a list
    # all details are returned in one single function, let's see if this works
    @sp.offchain_view(pure = True)
    def viewTokenDetails(self, token_id):
        #TODO: checking existence of the token_id
        return [self.tokenData[token_id].isbn,
        self.bookInfo[self.tokenData[token_id].isbn].unEncryptedBookDetailsCID,
        self.tokenData[token_id].copyNumber,
        self.tokenData[token_id].resalePrice,
        self.tokenData[token_id].isUpForResale,
        self.tokenData[token_id].isUpForRenting,
        self.tokenData[token_id].rentedAtTime,
        self.tokenData[token_id].rentingPrice]
    
    
    # get the lis of all books that's been published
    # returns the whole list, and frontend can be populated accordingly
    @sp.offchain_view(pure=True)
    def viewAllPublishedBooks(self):
        return sp.list(self.publishedBooks)
    
    # get the set of tokens put for sale
    @sp.offchain_view(pure=True)
    def viewTokensForSale(self):
        return sp.set(self.upForResaleTokens)
    
    # get the set of tokens put for rent
    @sp.offchain_view(pure=True)
    def viewTokensForRent(self):
        return sp.set(self.upForRentingTokens)
    
    # view a given book details
    @sp.offchain_view(pure=True)
    def viewBookDetails(self, isbn):
        sp.verify(self.bookInfo[isbn] != sp.address(0))
        return [self.bookInfo[isbn].unEncryptedBookDetailsCID,
                        self.bookInfo[isbn].publisherAddress,
                        self.bookInfo[isbn].bookPrice,
                        self.bookInfo[isbn].transactionCut,
                        self.bookInfo[isbn].bookSales]
    
    # view own book details, including the content. For the book's publisher
    @sp.offchain_view(pure=True)
    def viewMyBookDetails(self, isbn):
        sp.verify(self.bookInfo[isbn] != sp.address(0))
        sp.verify(self.bookInfo[isbn].publisherAddress == sp.sender, message="You're not the book publisher")
        return sp.record(self.bookInfo[isbn])  # returns the whole record.