from helpim.utils import OrderedDict

class StatsProvider():
    '''Apps can subclass StatsProvider to populate statistics'''

    '''
    Maps internally used stat names to name that can be shown to the user (i.e. table heading).
    Determines order in which stats are displayed. 
    '''
    knownStats = OrderedDict()

    @classmethod
    def render(cls, listOfObjects):
        '''Takes a list of data objects and generates the stats.
        Returns an OrderedDict which maps aggregation groups to another OrderedDict which maps stat names to stat results.
        These stat names can be translated to human readable strings with getStatTranslation(). 
        The OrderedDicts are necessary for easy iteration and display in a table.
        '''
        raise NotImplementedError("Subclass should implement this method.")

    @classmethod
    def countObjects(cls):
        '''Returns a list of dictionaries which is used to provide pagination through the stats.
        The dictionary needs to have the keys 'count' (number of objects on that page) and 'value' (name of the page).
        '''
        raise NotImplementedError("Subclass should implement this method.")

    @classmethod
    def aggregateObjects(cls, whichYear):
        '''Returns a list of data objects matching the filter given as first parameter. The objects returned here will be analyzed.'''
        raise NotImplementedError("Subclass should implement this method.")
    
    @classmethod
    def get_detail_url(cls):
        """Optionally return a URL that shows the singular objects being aggregated in the stats overview. Also see stats_details filter"""
        return None

    @classmethod
    def get_short_name(cls):
        raise NotImplementedError("Subclass should implement this method.")

    @classmethod
    def get_long_name(cls):
        raise NotImplementedError("Subclass should implement this method.")


class EventLogProcessor():
    def __init__(self, listOfEvents, listOfFilters):
        self.currentSession = None
        self.events = listOfEvents
        self.filters = listOfFilters

    def run(self, resultDict):
        for event in self.events:
            if self.currentSession != event.session:
                # pick up results
                [self._pickupResult(f, resultDict) for f in self.filters if f.hasResult()]

                # continue with next session
                self.currentSession = event.session
                map(lambda f: f.start, self.filters)

            map(lambda f: f.processEvent(event), self.filters)

        # check last session for results
        [self._pickupResult(f, resultDict) for f in self.filters if f.hasResult()]

    def _pickupResult(self, filter, resultDict):
        key = filter.getKey()
        if key in resultDict:
            filter.addToResult(resultDict[key])


class EventLogFilter():
    def start(self):
        pass

    def processEvent(self):
        pass

    def addToResult(self, result):
        pass

    def hasResult(self):
        pass

    def getKey(self):
        pass
