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
                            rentedAtBlock = sp.TNat,  #Tezos has the concept of time, so this might need rewriting for efficiency.
                            numberOfBlocksToRent = sp.TNat)


        # tokenId to TokenDetails big_map
        self.tokenData = sp.big_map(tkey = sp.TNat, tvalue = self.tokenDetails)


        # The big_map for holding all the list of rented tokens, for each address
        self.rentedTokensOfEach = sp.list(t = sp.TNat)
        self.rentedTokens = sp.big_map(tkey = sp.TAddress, tvalue = self.rentedTokensOfEach)

        # List of tokens up for resale. Don't need a mapping here.
        self.upForResaleTokens = sp.list(t = sp.TNat)
    
    
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
        self.bookInfo[params.isbn].bookSales += 1
        self.tokenData[params.token_id].isbn = params.isbn
        self.tokenData[params.token_id].copyNumber = self.bookInfo[params.isbn].bookSales
        self.tokenData[params.token_id].rentee = sp.address(0)
        sp.send(self.bookInfo[params.isbn].publisherAddress, sp.amount)


        # const contract = Sp.contract<TUnit>("tz1..." as TAddress).openSome("Invalid contract")
        # Sp.transfer(Sp.unit, 0, contract)


    # put the already purchased token for sale, by the tokenOwner

    @sp.entry_point
    def putTokenForSale(self, params):
        sp.verify(self.data.ledger[(sp.sender, params.token_id)], message = "Not authorized") #this check could be wrong.
        sp.verify(self.tokenData[params.token_id].isUpForRenting == False, message = "Can't put for sale while on rent")
        sp.verify(params.resalePrice > 0) # a greater-than-zero price is required.
        # TODO: Add a verify for renting period being over. 
        self.tokenData[params.token_id].resalePrice = params.resalePrice
        self.tokenData[params.token_id].isUpForResale = True
        self.upForResaleTokens.push(params.token_id)



