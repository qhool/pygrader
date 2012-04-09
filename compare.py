#Damerau-Levenshtein distance
def lev(a, b, depth = 5):
    if not a: return len(b)
    if not b: return len(a)
    if depth <= 0:
        return abs(len(a)-len(b)) + min(len(a),len(b))*0.5
    v = compare_vals(a[0],b[0])
    if v >= 0.5:
        return (1.0 - v) + lev( a[1:], b[1:])
    v = compare_vals(a[len(a)-1],b[len(b)-1])
    if v >= 0.5:
        return (1.0 - v) + lev(a[:len(a)-1],b[:len(b)-1],depth-1)
    return min(lev(a[1:], b[1:],depth-1)+(1 - compare_vals(a[0],b[0])), \
                   lev(a[1:], b, depth-1)+1, lev(a, b[1:],depth-1)+1)

def isdict(v):
    try:
        v.iterkeys()
    except:
        return False
    else:
        return True

def isiter(v):
    try:
        iter(v)
    except:
        return False
    else:
        return True


def compare_vals( a, b, float_precision = 8):
    multiplier = 1.0
    if a == None or b == None:
        if a == b:
            return multiplier
        else:
            return 0.0
    if type(a) != type(b):
        #print type(a), type(b)
        multiplier = 0.5
        if type(a) == str or type(b) == str:
            a = str(a)
            b = str(b)
        elif isiter(a) or isiter(b):
            if not isiter(b):
                b = [b]
            elif not isiter(a):
                a = [a]
        else:
            if type(a) == type(float()) and type(b) == type(int()):
                a = int(a)
            elif type(a) == type(int()) and type(b) == type(float()):
                a = float(a)
            else:
                return 0
    if type(a) == type(str()) and type(b) == type(str()) and \
            len(a) <= 1 and len(b) <= 1:
        if a == b:
            return multiplier
        elif a.lower() == b.lower():
            return multiplier*0.5
        else:
            return 0.0
    elif type(a) == set and type(b) == set:
        if len(a) == len(b) == 0:
            return multiplier
        else:
            return multiplier * float(len(a&b)) / float(len(a|b))
    elif type(a) == dict and type(b) == dict:
        aks = set(a.keys())
        bks = set(b.keys())
        if len(aks|bks) == 0:
            if len(aks&bks) == 0:
                return multiplier
            else:
                return 0.0
        multiplier = multiplier * compare_vals( aks, bks )
        return multiplier * sum( map( lambda k: compare_vals(a[k],b[k]), aks & bks ) ) / len(aks|bks)
    elif isiter(a) and isiter(b):
        if len(a) == 0 and len(b) == 0:
            return multiplier
        if a == b:
            return multiplier
        score = 0.5
        #score = min(1.0,1.0 - max(0.0,lev(list(a),list(b))*2.0/float((len(a)+len(b)))))
        return multiplier * 0.75 * compare_vals( set(map(str,a)), set(map(str,b)) )
    elif type(a) == type(float()):
        if abs(a-b) < 10**(-float_precision):
            return multiplier
        else:
            return 0.0
    elif type(a) == type(int()):
        if a == b:
            return multiplier
        else:
            return 0.0
    else:
        return 0
