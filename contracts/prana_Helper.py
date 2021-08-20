import smartpy as sp

class pranaHelper(sp.contract):

    def __init__(self) -> None:
        super().__init__()
        self.pranaAddress = sp.TAddress
        self.flag = sp.TBool
        self.flag = False
    
    @sp.entry_point
    def setPranaAddress(self, address):
        sp.verify(self.flag == False)
        self.pranaAddress = address
        self.flag = True

    @sp.entry_point
    def mintAToken(self, params):
        prana = sp.contract(sp.TRecord(isbn = sp.TNat, tokenOwner = sp.TAddress), self.pranaAddress, entry_point = "directPurchase").open_some() #sp.TInt needs to changed to params reference
        # calls prana with sp.amount as the money, and params as the argument. But need to resolve params though
        sp.transfer(params, sp.tez(sp.amount), prana)

    def buyTokenFromPrana(self, params):
        prana = sp.contract(sp.TRecord(token_id = sp.TNat, tokenBuyer = sp.TAddress), self.pranaAddress, entry_point = "buyToken").open_some() 
        sp.transfer(params, sp.tez(sp.amount), prana)