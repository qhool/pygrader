import os
import re

scores = {}
assignments = map( lambda x: list(), range(8) )

topdir = 'feedback'
for d in os.listdir(topdir):
    if re.match( 'a(\d)', d ):
        assignment = int(re.match( 'a(\d)', d ).group(1))
        for fname in os.listdir(os.path.join(topdir,d)):
            if re.match( '(\w+).txt', fname ):
                student = fname.split('.')[0]
                f = open( os.path.join(topdir,d,fname) )
                nscores = 0
                totscores = 0
                score = 0
                for line in f.readlines():
                    m = re.match( 'score: ([0-9\.]*)$', line )
                    if m:
                        nscores += 1
                        totscores += float(m.group(1))
                        score = totscores / nscores
                f.close()
                #print "{0} / {1} / {2}".format( assignment, student, score )
                if not scores.has_key( student ):
                    scores[student] = [0] * 8
                scores[student][assignment-1] = score
                assignments[assignment-1].append(score)
                
for a in assignments:
    a.sort()

percentiles = {}
for student in scores:
    s = scores[student]
    percentiles[student] = []
    for i in range(len(s)):
        if s[i] == 0.0:
            percentiles[student].append(0.0)
        else:
            percentiles[student].append( sum( map( lambda x: 1.0 if s[i] >= x else 0, assignments[i] ) )/len(assignments[i]) )
    #print "{0}: {1}".format(student, percentiles[student])

bar_len = 5
def mk_bar(x,c):
    bar_n = int(x*(bar_len+1))
    if bar_n == 0:
        bar_n = 1
        c = '_'
    bar = c * bar_n + ' ' * (bar_len - bar_n)
    return bar

def prn_chart(student):
    s = scores[student]
    p = percentiles[student]
    out = []
    scale_space = " " * (bar_len - 2)
    out.append( " 0" + scale_space + "1" )
    out.append( " ." + scale_space + "." )
    out.append( " 0" + scale_space + "0" )
    out.append( " " + "-" * bar_len )
    out.append( " " + " " * bar_len )
    out.append( " " + " " * bar_len )
    for a in [0,1,2,3,4,6,7]: 
        out.append( "a" + mk_bar( s[a], "#" ) )
        out.append( str(a) + mk_bar( p[a], "|" ) )
        out.append( " " + " " * bar_len )

    rot = []
    for i in range(bar_len,-1,-1):
        rot.append( "".join( map( lambda line: line[i], out ) ) )
    print "\n".join(rot)

for stdn in sorted( scores.keys(), key = lambda s: s[1:] + s[0] ):
    print "\n" + "-=" * 30 + "\n"
    print stdn, "\n"
    prn_chart(stdn)
    print "\n\n"



