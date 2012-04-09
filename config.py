import json
import re
import bunch
import pprint
import datetime

class DateError(Exception):
    def __init__(self,date_str):
        self.date_str = date_str
    def __str__(self):
        return "Could not parse date value: {0}".format( self.date_str )

date_formats = [ 
    { 'pattern': "(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})" }
    ]

#precompile patterns
for d in date_formats:
    d['re'] = re.compile( d['pattern'] )

def parse_date( dt ):
    for d in date_formats:
        m = d['re'].match( dt )
        if m != None:
            return datetime.datetime( *map( int, m.groups()) ) 
    raise DateError( dt )
    
def load_file( fname, key = None ):
    try:
        f = open( fname, 'r' )
    except IOError:
        return {}
    try:
        dat = json.load( f )
        if key == None:
            return dat
        else:
            return { key : dat }
    except ValueError:
        f.seek(0)
        stuff = f.read()
        if re.match( '\s*$', stuff ):
            return {}
        else:
            raise

cfg = {}
cfg.update( load_file( 'main.cfg.base' ) )
cfg.update( load_file( 'main.cfg' ) )
cfg.update( load_file( 'assignments.cfg', 'assignments' ) )

def _bunchify( key, vals, tabs ):
    if type(vals) == type(dict()):
        if __name__ == '__main__':
            print ""
        b = bunch.Bunch( )
        for k in vals.iterkeys():
            if __name__ == '__main__':
                print tabs + k + ": ", 
            b[k] = _bunchify( k, vals[k], tabs + "    " )
        return b
    elif type(vals) == type(list()):
        if __name__ == '__main__':
            print ""
        counter = { 'i': 0 }
        def _subbunch( x ):
            if __name__ == '__main__':
                print tabs + "[{0:2}]: ".format( counter['i'] ), 
            counter['i'] = counter['i'] + 1
            #for a list, just use the key from the level above 
            return _bunchify( key, x, tabs + "    " )
        return map( _subbunch, vals )
    else:
        if __name__ == '__main__':
            print vals
        if re.search( 'date', key ):
            return parse_date( vals )
        else:
            return vals

for k in cfg.iterkeys():
    if __name__ == '__main__':
        print k + ": ",
    globals()[k] = _bunchify(k,cfg[k], "    " )


#if __name__ == '__main__':
#    pp = pprint.PrettyPrinter(indent=4)
#    pp.pprint( cfg['repository'] )
#    pp.pprint( cfg['system'] )
#    pp.pprint( cfg['assignments'] )
