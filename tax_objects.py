'''
Classes and methods to facilitate the tracking of crypto lots (chunks of cryptocurrency bought at the same time and place)
'''
import datetime 
import copy
import decimal
import pandas as pd

class Lot(object):
    '''object is sorted by date purchased'''
    def __init__(self,quantity,cost_basis,date_purchased,date_sold=None):#,pool_id):
        self.quantity       = decimal.Decimal(abs(quantity))
        self.cost_basis     = decimal.Decimal(abs(cost_basis))
        self.date_purchased = pd.to_datetime(date_purchased)
        self.date_sold      = pd.to_datetime(date_sold)
        # if date_purchased is None or isinstance(date_purchased,datetime.datetime):
        #     self.date_purchased = date_purchased
        # else:
        #     self.date_purchased = datetime.datetime.fromisoformat(date_purchased)
        #self.asset          = asset.upper()
        # if date_sold is None or isinstance(date_sold,datetime.datetime):
        #     self.date_sold = date_sold
        # else:
        #     self.date_sold      = datetime.datetime.fromisoformat(date_sold)
        #self.pool_id = pool_id
        self.lot_id         = None     #probably use something like a hash function to create a unique hash 

    def _empty_lot(self):
        self.quantity   = decimal.Decimal(0)
        self.cost_basis = decimal.Decimal(0)
        #self.pool_id = None

    def assign_id(self,id):
        self.lot_id = id 

    @property
    def id(self):
        return self.lot_id

    def sell(self,quantity=None,date_sold=datetime.datetime.now(),MAX_DELTA=0.00000001):
        # if not isinstance(date_sold,datetime.datetime):
        #     date_sold = datetime.datetime.fromisoformat(date_sold)
        date_sold = pd.to_datetime(date_sold)
        if quantity is None:
            quantity = self.quantity  #putting None is equivalent to selling entire lot
        if not isinstance(quantity,decimal.Decimal):
            quantity = decimal.Decimal(quantity)
        
        diff = self.quantity - quantity
        if diff > MAX_DELTA:
            updated_cost_basis = (self.cost_basis * diff) / self.quantity
            updated_quantity   = self.quantity - quantity
            remaining = 0

            #------------------
            # The portion that gets sold will be a new lot with extra information
            sold_cost_basis = self.cost_basis - updated_cost_basis
            sold_lot = Lot(quantity,sold_cost_basis,self.date_purchased,date_sold)   #CREATING NEW LOT TO RETURN 

            #------------------
            # Updating the values in the current lot
            self.quantity   = updated_quantity
            self.cost_basis = updated_cost_basis

        else:
            sold_lot = copy.deepcopy(self)
            self._empty_lot()
            sold_lot.date_sold = date_sold
            remaining      = abs(diff)

        return remaining, sold_lot
    
    #-----Overloading----------------
    def __repr__(self):
        return f"< Lot id={self.id} quantity = {self.quantity:12.8f} basis = {self.cost_basis:6.2f} purchased = {self.date_purchased:%Y-%m-%d %H:%M:%S} >" 

    #-----Comparison Operators-------
    def __lt__(self,other_lot):
        return self.date_purchased < other_lot.date_purchased

    def is_empty(self,MAX_DELTA=0.00000001):
        return self.quantity <= MAX_DELTA

    #-----Utility Methods------------
    def _reset_date_sold(self):
        self.date_sold = None



class Pool(object):
    """A pool is designed to represent an exchange or maybe more accurately a wallet.
    
    For example, let's say I buy 1 BTC in Coinbase and then send half of it to a hardware wallet, such as 
    a ledger or a Trezor device.
    In this case, we would create a `Lot` object to represent the 1 BTC purchase. Additionally, we 
    need to create one `Pool` object for Coinbase and one for Ledger and use the transfer method to
    transfer the lot from the coinbase pool to the ledger pool.
    
    Example Usage:
    --------------

    >>> coinbase_pool = Pool('Coinbase','BTC')
    >>> ledger_pool   = Pool('Ledger','BTC')

    >>> lot = Lot(1.0,4500,'2017-06-01 10:30')
    >>> coinbase_pool.add_lot(lot)

    >>> coinbase_pool.transfer(0.5, ledger_pool)

    """
    def __init__(self,name,asset,addresses=[]):
        self.name    = name
        self.asset   = asset.upper()
        self.lots    = []
        self.pool_id = None     # same as above, probably use something like a hash function to create a unique identifier
        #self.lot_id_to_idx = dict()
        self.addresses = addresses
        #self.avg_cost_basis = 0

    def add_lot(self,lot_object):
        self.lots.append(lot_object)

        #I could probably write this more efficiently but I am in a hurry right now.
        self.lots = sorted(self.lots)
        #self._compute_cost_basis()

    def remove_lot(self,lot_id):
        # idx_to_remove = []
        # popped_items = []
        # if isinstance(lot_id,list):
        #     for i in range(len(self.lots)):
        #         lot = self.lots[i]
        #         if lot.lot_id in lot_id:
        #             idx_to_remove.append(i)
        #             lot_id.remove(lot.lot_id)
        #             popped_items.append(self.lots.pop(i))

        for i in range(len(self.lots)):
            lot = self.lots[i]
            if lot.lot_id == lot_id:
                return self.lots.pop(i)

    def get_max_delta(self,decimal_accuracy=8):
        dec_acc = '0.' + '0'*(decimal_accuracy-1) + '1'
        MAX_DELTA = float(dec_acc)
        return MAX_DELTA

    def sell(self,quantity,date_sold=datetime.datetime.now(),method='fifo',decimal_accuracy=8):
        # if not isinstance(date_sold,datetime.datetime):
        #     date_sold = datetime.datetime.fromisoformat(date_sold)

        date_sold = pd.to_datetime(date_sold)

        MAX_DELTA = self.get_max_delta(decimal_accuracy)
        lots_sold = []
        idx = 0
        while quantity > MAX_DELTA:
            lot = self.lots[idx]
            quantity,sold_lot = lot.sell(quantity,date_sold,MAX_DELTA=MAX_DELTA)
            lots_sold.append(sold_lot)

            #if lot.is_empty():
            #print(f"Lot position={idx} quantity={self.quantity:.8f} remaining left={quantity:.8f}")
            if quantity > MAX_DELTA:
                idx += 1  #only increment if we have depleted this lot

        assert(quantity<=MAX_DELTA)

        #delete lots that are empty
        self.lots = [lot for lot in self.lots if not lot.is_empty(MAX_DELTA=MAX_DELTA)]
        return lots_sold

    def transfer(self,quantity,target_pool,date=datetime.datetime.now(),method='fifo',fees=0,decimal_accuracy=8):
        '''if fee is provided, it is assumed that it is taken from `quantity`. Therefore, 
        the source pool will lose an amount equal to `quantity` and the target pool will receive
        an amount equal to `quantity - fee`.
        
        decimal_accuracy: int
            Number of decimals that will be taken into account for calculations. Default is 8, so that will 
            create a MAX_DELTA of 0.00000001. A value `decimal_accuracy=1` will result in `MAX_DELTA=0.1`
        '''
       
        MAX_DELTA = self.get_max_delta(decimal_accuracy)  #difference in value because of precison allowed by comparisions of equality
        assert(isinstance(target_pool,Pool))

        date = pd.to_datetime(date)

        checksum_start = self.quantity + target_pool.quantity

        self.sell(fees)                       #fees are discounted first and then the remainder is calculated
        adjusted_quantity = quantity - fees
        lots = self.sell(quantity,decimal_accuracy=decimal_accuracy)            #transferring is basically the same as selling from the calculation stand-point. I only need to remove the sold date
        
        # Now we just add the lots to the target pool and reset their date_sold parameter
        for lot in lots:
            lot._reset_date_sold()
            
            target_pool.add_lot(lot)

        try:
            # We need to make sure no coins were accidentally double-spent or created during this process
            checksum_end = self.quantity + target_pool.quantity
            diff = abs(checksum_start - checksum_end)
            assert(diff <= MAX_DELTA)

        except AssertionError as e:
            print(f"\n{'-'*80}\n---> ***ERROR***: {e}\n{'Date':20} = {date}\n{'Checksum_start':20} = {checksum_start}\n{'Checksum_end':20} = {checksum_end}\n{'Diff':20} = {diff}")
            print(f"{'self.quantity':20} = {self.quantity}\n{'target_pool.quantity':20} = {target_pool.quantity}\n")

    def receive(self,quantity,source_pool,date_transafered=None,method='fifo',fees=0,decimal_accuracy=8):
        '''Basically the reverse of Transfer. This function is here mainly for convenience and clarity.'''
        source_pool.transfer(quantity,self,date=date_transafered,fees=fees,decimal_accuracy=decimal_accuracy)

    def show_lots(self):
        try:
            date_len  = len(f"{self.lots[0].date_purchased:%Y-%m-%d %H:%M:%S}")
        except IndexError:
            date_len  = 15
        
        quant_len = 12
        basis_len = 11
        support_line_len = 10 + date_len + quant_len + basis_len

        print(f"\n{'='*52}\nPool: {self.name}\tAsset: {self.asset}")
        print(f"\n| {'Date Purchased':^{date_len}} | {'Quantity':^{quant_len}} | {'Cost Basis':^{basis_len}} |")
        print(f"{'-'*support_line_len}")
        for lot in self.lots:
            print(f"| {lot.date_purchased:%Y-%m-%d %H:%M:%S} | {lot.quantity:12.8f} | ${lot.cost_basis:<10.2f} |")
    
        print(f"\nTotal quantity: {self.quantity:>.8f} {self.asset}")

    def history(self):
        '''Show activity history by a collection of TransactionEvent objects'''
        pass 

    #======================================
    @property
    def cost_basis(self):
        return sum([lot.cost_basis for lot in self.lots])
    
    @property
    def quantity(self):
        return sum([lot.quantity for lot in self.lots])

    
    def __repr__(self):
        name       = self.name.upper()
        asset      = self.asset.upper()
        quantity   = self.quantity
        cost_basis = self.cost_basis

        try:
            price_per_coin = cost_basis / quantity
        except (ZeroDivisionError, decimal.InvalidOperation):
            price_per_coin = 0

        return f"< {name:^10} Pool ({asset:^3}), quantity = {quantity:<12.8f}, cost basis = ${cost_basis:<6.2f} @ ${price_per_coin:<6.2f} per {asset:<4} >"

class Exchange(object):
    '''An exchange represents a real life exchange but also a wallet.
    The purpose of this class is to more easily bundle different coins
    together if they are in the same account or hardware wallet, for instance.'''
    def __init__(self,exchange_name, pool_names_assets=[]):
        '''
        pool_names_assets: list of tuples
            List of tuples with the name of the pool and the coin associated with that pool. For example:
            
            >>> pools = [("BTC", "BTC"),
                         ("Coinbase Eth","ETH"),
                         ("Some name...", "LTC"),
                         ("... ... ...", "ADA"),]
            
            >>> ex = Exchange(exchange_name='Binance', pool_names_assets=pools)

            If only a string is provided, instead of a tuple in the list, then the class will use that string as
            both the name and the asset ticker. An example:

            >>> pools = ["BTC",
                         ("this is a tuple","DOT"),
                         "NAV",]

            In the example above, a `Pool` object for `BTC` will be created with the following parameters:
            >>> Pool(name="BTC", asset="BTC")

        '''
        self.name = exchange_name
        self.pools = dict()
        #self.assets = []
        for pool_info in pool_names_assets:
            if isinstance(pool_info,tuple):
                name  = pool_info[0]
                asset = pool_info[1].upper()
            elif isinstance(pool_info,str):
                name  = pool_info
                asset = pool_info.upper()
            else:
                print(f"Could not create pool from `{pool_info}`. `pool_names_assets` should be a list of tuples or a list of strings.")
                continue
            
            if asset in self.pools:
                print(f"\nMultiple pools of the same asset are not supported in the same exchange at the moment")
                print(f"Pool for ticker {asset.upper()} already exists.\n Existing pools: {self.pools.keys()}\n")
                continue

            self.pools[asset] = Pool(name=name,asset=asset)

    def add_pool(self,pool_name,asset):
        self.pools[asset] = Pool(name=pool_name,asset=asset)

    
    def get_pool(self,asset):
        return self.pools.get(asset,None)

    
    @property 
    def assets(self):
        return list(self.pools.keys())

##============================================================================
## This section implements objects that deal with records, so transactions like buying, selling,
##   transfering, converting, mining, earning, etc. crypto will be accounted for.


class TransactionEvent(object):
    ALLOWED_TX_TYPES = ['buy','sell','transfer','income']
    def __init__(self,tx_type,date,from_quantity,to_quantity,from_asset,to_asset):
        try:
            assert(tx_type.lower() in self.ALLOWED_TX_TYPES)
        except AssertionError as e:
            print(f"\n{'='*80}\n{e}\nTransaction type must be one of: {self.ALLOWED_TX_TYPES} | Given: {tx_type.lower()}\n")

        self.tx_type       = tx_type.lower()
        self.date          = pd.to_datetime(date)
        self.from_quantity = decimal.Decimal(from_quantity)
        self.to_quantity   = decimal.Decimal(to_quantity)
        self.from_asset    = from_asset.upper()
        self.to_asset      = to_asset.upper()

    def __lt__(self,other):
        return self.date < other.date

    def is_buy(self):
        return self.tx_type.lower()=='buy'
    
    def is_sell(self):
        return self.tx_type.lower()=='sell'
    
    def is_transfer(self):
        return self.tx_type.lower()=='transfer'

    def is_income(self):
        return self.tx_type.lower()=='income'

    @property 
    def type(self):
        return self.tx_type

class BuyEvent(TransactionEvent):
    def __init__(self,quantity,cost_basis,asset,date):
        quantity = abs(quantity)
        cost_basis = abs(cost_basis)
        super().__init__(tx_type='buy',date=date,from_quantity=cost_basis,
                         to_quantity=quantity,from_asset='USD',to_asset=asset)

    def __repr__(self,):
        price_per_coin = self.from_quantity / self.to_quantity
        return f"< {'BUY event:':<11} {self.to_quantity:>.8f} {self.to_asset:<3} for {self.from_quantity:>6.2f} {self.from_asset:<3} @ {price_per_coin:>6.2f} per {self.to_asset:<3} on {self.date:%Y-%m-%d %H:%M}>"

class SellEvent(TransactionEvent):
    def __init__(self,quantity,proceeds,asset,date):
        quantity = abs(quantity)
        super().__init__(tx_type='sell',date=date,from_quantity=quantity,
                         to_quantity=proceeds,from_asset=asset,to_asset='USD')

    def __repr__(self):
        price_per_coin = self.to_quantity / self.from_quantity
        return f"< {'SELL event:':<11} {self.from_quantity:>.8f} {self.from_asset:<3} for {self.to_quantity:>6.2f} {self.to_asset:<3} @ {price_per_coin:>6.2f} {self.to_asset:<3} per 1 {self.from_asset:<3} on {self.date:%Y-%m-%d %H:%M} >"

class FeeEvent(SellEvent):
    '''A fee will be almost the same as a Sell event, except that proceeds would be negative. This just adds
    some boilerplate code to '''
    def __init__(self,quantity,market_value,asset,date):
        quantity = abs(quantity)
        super().__init__(quantity=quantity,proceeds=-market_value,asset=asset,date=date)

    def __repr__(self):
        return f"< FEE event: Paid {self.from_quantity:>.8f} {self.from_asset:<3} or {self.to_quantity:>6.2f} {self.to_asset:<3} ON {self.date:%Y-%m-%d %H:%M}"

class TransferEvent(TransactionEvent):
    def __init__(self,quantity,asset,source_pool_id,target_pool_id, date, network_fees=0):
        quantity          = abs(quantity)
        self.network_fees = abs(network_fees)
        final_quantity    = quantity - self.network_fees

        super().__init__(tx_type='transfer', date=date, from_quantity=quantity,to_quantity=final_quantity,from_asset=asset,to_asset=asset)
        self.source_pool_id = source_pool_id
        self.target_pool_id = target_pool_id

    def __repr__(self):
        return f"< {'TRANSFER event:':<11} {self.from_quantity:>.8f} {self.from_asset:<3} FROM `{self.source_pool_id}` TO `{self.target_pool_id}` ON {self.date:%Y-%m-%d %H:%M} >"


class IncomeEvent(TransactionEvent):
    def __init__(self,quantity,market_value,asset,date,expenses=0):
        self.quantity     = quantity
        self.market_value = market_value
        self.asset        = asset
        self.date         = date
        self.expenses     = expenses 

        #super().__init__(quantity=quantity,cost_basis=cost_basis,asset=asset,date=date)

    @property
    def reportable_income(self):
        return self.market_value - self.expenses

    def __repr__(self):
        price_per_coin = self.market_value / self.quantity
        return f"< {'INCOME event:':<11} {self.quantity:>.8f} {self.asset:<3} for {self.market_value:6.2f} USD @ {price_per_coin:6.2f} per {self.asset:<3} ON {self.date:%Y-%m-%d %H:%M} >"

class EarnEvent(TransactionEvent):
    '''This is for transactions that should count as regular income.
    For example: cryptocurrency mining, crypto rewards such as the ones from Coinbase Earn program,
    and staking rewards.'''

    def __init__(self,quantity,cost_basis,asset,date,expenses=0):
        self.income_event = IncomeEvent(quantity=quantity, market_value=cost_basis, asset=asset, date=date, expenses=expenses,)
        self.buy_event   = BuyEvent(quantity=quantity, cost_basis=cost_basis, asset=asset, date=date)

class ConvertEvent(TransactionEvent):
    def __init__(self,from_quantity,to_quantity,from_asset,to_asset,usd_proceeds,date,tx_fees=0,tx_fees_asset=None):
        self.tx_fees = tx_fees
        if tx_fees_asset is None or tx_fees_asset.upper()==from_asset.upper():
            self.tx_fees_asset = from_asset   #if no coin is specified, it is assumed that the same coin being traded is used to pay the fee
            from_quantity += self.tx_fees   #if the coin used is the same, then we add this fee on top

            self.fee_event = None

        elif tx_fees_asset.upper() == 'USD':
            self.tx_fees_asset = tx_fees_asset
            usd_proceeds -= self.tx_fees

            self.fee_event = None

        else:
            #sometimes the coin to pay the fee is different 
            #   than the coins being traded, for example when using 
            #   BNB coin in Binance to pay for commission fees on a BTC-ETH trade.
            self.tx_fees_asset = tx_fees_asset.upper()  
            
            #FIND THE Market PRICE of the fee Coin at the time of transaction and subtract it from proceeds
            #Also, some BUY event probably needs to be created for the fee COIN

            usd_fee_value = 0    # -> FIND the MARKET PRICE. Also, this value should be discounted from proceeds
            self.fee_event = SellEvent(quantity=tx_fees,proceeds=usd_fee_value,asset=tx_fees_asset,date=date)

            usd_proceeds -= usd_fee_value
                

        self.sell_event = SellEvent(quantity=from_quantity,proceeds=usd_proceeds,asset=from_asset,date=date)
        self.buy_event  = BuyEvent(quantity=to_quantity,cost_basis=usd_proceeds,asset=to_asset,date=date)