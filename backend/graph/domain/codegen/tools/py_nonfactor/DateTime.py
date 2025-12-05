from L3FactorFrame.FactorBase import FactorBase
from L3FactorFrame.tools.DecimalUtil import isEqual, notEqual

class DateTime(FactorBase):
    def __init__(self, config, factorManager, marketDataManager):
        super().__init__(config, factorManager, marketDataManager)

    def calculate(self):
        ts = self.getPrevTick("DateTime")
        self.addFactorValue(ts)
