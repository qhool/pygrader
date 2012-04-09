import os
import os.path
import check_utils
import random
import re
import math
import copy
import string
import inspect
from inspect import ArgSpec

def get_start( dir, score_multiplier, output = "", 
               filename = "start.py", file_filter = None ):
    found, file, dispfile = check_utils.choose_file( dir, filename, file_filter ) 
    if not found:
        output += "{0} not found ".format( filename )
        if file == None:
            output += "and no suitable replacement.\n"
            score_multiplier = 0.0
        else:
            output += ", using {0} and reducing final score by 20%.\n".format( dispfile )
            score_multiplier *= 0.8
    else:
        output += "checking {0}\n".format( dispfile )
    return ( file, dispfile, score_multiplier, output )

def comments_message( file, dispfile, score_multiplier, output = "", penalty = 0.1):
    ratio = check_utils.comment_ratio( file )
    if ratio == 0.0:
        output += "{f} has no comments.".format( f = dispfile )
        if penalty != None:
            output += "  Reducing score by {p:.0%}.\n".format( p = penalty )
            score_multiplier *= (1.0 - penalty)
        else:
            output += "\n"
    else:
        output += "{f} is {rat:.0%} comments.  ".format( f=dispfile, rat=ratio )
        if ratio > 0.75:
            output += "Almost certainly too much."
        elif ratio > 0.5:
            output += "Try for brevity"
        elif ratio > 0.25:
            output += "Thoroughly commented"
        elif ratio > 0.1:
            output += "Probably a good amount."
        elif ratio > 0.05:
            output += "More comments might be helpful."
        elif ratio > 0.02:
            output += "Only OK if your code is very clear."
        else:
            output += "MOAR!"
        output += "\n"
    return ( score_multiplier, output )

def a1( dir ):
    file, dispfile, score_multiplier, output = get_start( dir, 1.0, "" )
    score = 1.0
    inp = "\n" * 10
    (ev, out, err) = check_utils.wrap_assignment( file, inp )
    matches = re.finditer( r"((?:\w+\.)?\w+)@((\w+\.)+\w+)", out )
    found_ncf = False
    found = []
    for m in matches:
        found.append( m.group() )
        if m.group(2) == 'ncf.edu':
            output += "{0} looks like an ncf email address\n".format( 
                m.group() )
            found_ncf = True
    if len(found) == 0:
        output += "No email address found\n"
        score = 0.0
    elif not found_ncf:
        output += "Looking for NCF email address, got: {0}\n".format(
            ", ".join( found ) )
        score -= 0.6
    if len(found) > 1:
        output += "Only 1 email wanted, not {0} ({1}).\n".format( 
            len(found), ", ".join( found ) )
        score -= 0.2
    return (score*score_multiplier, output)


def a2( dir ):
    file, dispfile, score_multiplier, output = get_start( dir, 1.0, "" )
    score_multiplier, output = comments_message( file, dispfile,
                                                 score_multiplier, output,
                                                 penalty = None )
    if file == None:
        return ( score_multiplier, output )

    num_reg = "[-+]?\d+\.?\d*"
    wspace_punct_reg = "[\s()]*"
    eqn_regx = re.compile( 
        "({n}){w}x(?:\*\*|\^)2{w}\+?{w}({n}){w}x{w}\+?{w}({n})".format( 
            n=num_reg, w=wspace_punct_reg ) )
    root_regx = re.compile(
        "({n}){w}\+?{w}({n}){w}([ij])".format( n=num_reg, 
                                               w=wspace_punct_reg ) )
    prec_regx = re.compile("\.?(\d+)$")
    divider_regx = re.compile("^\*+$", re.MULTILINE)

    def run_assignment( a, b, c, prec, roots_only = False ):
        results = []
        def p_result( str ):
            results.append( str )
        if roots_only:
            score = 20
            max_score = 20
        else:
            score = 100
            max_score = 100

        words = map( lambda x: check_utils.randomword(8,12), range(6) )
        
        inp = "\n".join( map(str,[a, b, c, prec]) ) + "\n" + \
            "\n".join( words ) + "\n"*20 #extra lines in case it asks for it
        (ev, out, err) = check_utils.wrap_assignment( file, inp )
        root_matches = root_regx.finditer( out )
        root_strs = []
        if root_matches != None:
            for rmatch in root_matches:
                root_strs.append(rmatch.groups())
        #print "root strs: ", root_strs
        if not roots_only:
            #look for equation display:
            eqn_match = eqn_regx.search( out )
            if eqn_match == None:
                p_result( "quadratic not displayed" )
                score -= 10
            else:
                p_result( "quadratic: {0}".format( eqn_match.group() ) )

        if len(root_strs) == 0:
            p_result( "No roots generated" )
            score -= 20
        elif len(root_strs) > 2:
            p_result( "Too many roots ({0})".format( len(root_strs) ) )
            score -= 20
        elif len(root_strs) < 2:
            p_result( "Not enough roots" )
            score -= 20
        else:
            epsilon = 5*10**(-1*(prec - 1))
            for r in root_strs:
                x = complex( float(r[0]), float(r[1]) )
                val = a*x**2+b*x+c
                #val should be == 0
                if abs(val) > epsilon:
                    p_result( "Root {0} incorrect".format(x) )
                    score -= 10
                else:
                    p_result( "Root {0} correct".format(x) )
        
        
        if not roots_only:
            if len(root_strs) != 2:
                score -= 30
            else:
                root_nums = []
                ind_score = 0
                for r in root_strs[0:1]:
                    (ipart,rpart,ind) = r
                    root_nums.extend( [ipart,rpart] )
                    if ind != 'i':
                        if ind_score == 0:
                            p_result( "Root not displayed with 'i'" )
                        ind_score += 5
                        score -= ind_score
                prec_score = 0
                for n in root_nums:
                    m = prec_regx.search( n )
                    if m != None and len(m.groups(1)) > prec:
                        prec_score += 5
                if prec_score == 0:
                    p_result( "precision correct" )
                else:
                    p_result( "too many digits of precision" )
                score -= prec_score
            div_match = divider_regx.search( out )
            if div_match == None:
                p_result( "no divider" )
                score -= 10
            elif div_match.group() != "*" * (prec*4):
                p_result( "divider length is {0}, should be {1}".format(
                        len(div_match.group()), prec*4 ) )
                score -= 5
            else:
                p_result( "divider OK" )
            #look for words in madlib:
            words_found = 0
            for w in words:
                if re.search( w, out ):
                    words_found += 1
            if words_found < len(words):
                p_result( "Mad-Lib only uses {0} words".format(words_found) )
                score -= (len(words) - words_found) * 5
            else:
                p_result( "Mad-Lib correct" )
        return ( float(score)/float(max_score), results )
    
    init_score, results = run_assignment( 1,2,3,5 )
    output += "\n".join(results)+"\nTrying additional coefficients: "
    coefficient_scores = []
    for i in range(30):
        def rcoef():
            rc = random.uniform( -6, 12 )
            if rc == 0.0:
                rc = 0.01
            return rc
        try:
            cscore, res = run_assignment( rcoef(), rcoef(), rcoef(), 10 )
            coefficient_scores.append( cscore )
            if cscore > 0.9:
                output += "."
            elif cscore >= 0.5:
                output += "x"
            else:
                output += "X"
        except:
            coefficient_scores.append( 0.0 )
            output += "X"
    coef_score = math.fsum( coefficient_scores ) / len(coefficient_scores)
    output += " {0:.0%} correct\n".format(coef_score)
        
    final_score = (init_score * 0.7 + coef_score * 0.3)*score_multiplier
    return (final_score,output)

def a3( dir ):
    file, dispfile, score_multiplier, output = get_start( dir, 1.0, "" )
    score_multiplier, output = comments_message( file, dispfile,
                                                 score_multiplier, output,
                                                 penalty = 0.05 )

    max_score = (60+20)*30  #a few extra points for correct # lines, etc.
    score = max_score
    bf = open( 'checks/a3.txt', "r" )
    benchmark = map( lambda s: s.rstrip("\n"), bf.readlines() )
    bf.close()
    if file == None:
        return ( score_multiplier, output )
    (ev, out, err ) = check_utils.wrap_assignment( file, '' )
    #remove final newline, or it will add an extra empty str to lines
    lines = out.rstrip("\n").split("\n")
    if re.search( "@", lines[0] ):
        #move the email to the end:
        email = lines[0]
        lines = lines[1:]
        lines.append( email )
    if len(lines) != len(benchmark):
        output += "{desc} lines -- got {a} expecting {b}\n".format(
            desc = "Too many" if len(lines) > len(benchmark) else "Not enough",
            a = len(lines), b = len(benchmark) )
        output += "Comparing non-blank lines only: "
        score -= abs( len(lines) - len(benchmark) ) * 10 + 80
        def remove_blanks( lns ):
            return filter( lambda l: not re.match( '^\s*$', l ), lns )
        lines = remove_blanks( lines )
        benchmark = remove_blanks( benchmark )
    else:
        output += "Correct number of lines.\nComparing output: "
    def compare_lines( u, b ):
        longer = len(u) > len(b)
        matches = 0
        #print "len b: ", len(b)
        for i in range(len(b)):
            if len(u) <= i:
                break
            if b[i] == u[i]:
                matches += 1
        return (matches, longer)
    match_chars_total = 0
    for i in range(len(benchmark)):
        if len(lines) <= i:
            score -= 70
            #print "missing line: -70"
            #print score
            continue

        sl = lines[i]
        bl = benchmark[i]
        match_count, longer = compare_lines( sl, bl )
        if longer:
            score -= 10
        #print "good matches: ", match_count
        if match_count < 10:
            #allow some points back by comparing w/o whitespace:
            match2, longer = compare_lines( re.sub(r"\s", '', sl),
                                            re.sub(r"\s", '', bl) )
            match_count += int(float(match2)/3.0)
        match_chars_total += match_count
        #print "match count: ", match_count
        deduction = 60 - match_count
        #print "deduction: ",deduction
        score -= deduction if deduction > 0 else 0
        #print score
    output += "{0} characters match.\n".format( match_chars_total )
    return ((float(score)/float(max_score))*score_multiplier, output)

def a4( dir ):
    file, dispfile, score_multiplier, output = get_start( dir, 1.0, "" )
    score_multiplier, output = comments_message( file, dispfile,
                                                 score_multiplier, output,
                                                 penalty = 0.10 )
    if file == None:
        return ( score_multiplier, output )
    max_score = 270
    score = 0
    mod = check_utils.ModuleWrapper( file )

    mult_by_7_spec = ArgSpec( ['n','seven'], None, None, [ 7 ] )
    ok, output, score = mod.check_args( 'mult_by_7', output, score,
                                    multiplier = 10,
                                    pattern = mult_by_7_spec )
    if ok & ( mod.NOT_FOUND + mod.NOT_FUNC ) == 0:
        output += 'testing'
        def mb7( n, seven=7 ):
            return n * seven
        #check floats
        output, score = check_utils.check_func( 
            mod.mult_by_7, 
            check_utils.random_tuple_generator( lambda: random.gauss(0,30),
                                                count = 30, min_length = 1, 
                                                max_length = 2 ),
            check_utils.gen_evaluator( mb7 ),
            output, score )
        #check ints
        output, score = check_utils.check_func( 
            mod.mult_by_7, 
            check_utils.random_tuple_generator( lambda: int(random.gauss(0,100)),
                                                count = 30, min_length = 1, 
                                                max_length = 2 ),
            check_utils.gen_evaluator( mb7 ),
            output, score )
        output += "\n"
        
    ok, output, score = mod.check_args( 'add_it_up', output, score,
                                        multiplier = 10, min_args = 10 )
    if ok & ( mod.NOT_FOUND + mod.NOT_FUNC ) == 0:
        output += 'testing'
        def addup( *args ):
            return float(sum(args))
        #check floating point values:
        output, score = check_utils.check_func( 
            mod.add_it_up,
            check_utils.random_tuple_generator( lambda: random.gauss(0,30),
                                                count = 30, max_length = 10 ),
            check_utils.gen_evaluator( addup ),
            output, score )
        #check integer values:
        output, score = check_utils.check_func(
            mod.add_it_up,
            check_utils.random_tuple_generator( lambda: int(random.gauss(100,500)),
                                                count = 30, max_length = 10 ),
            check_utils.gen_evaluator( addup ),
            output, score )
        output += "\n"

    
    alphabet_backwards_spec = ArgSpec( ['last_letter','length'], None, None,
                                       ['Z', 26] )
    ok, output, score = mod.check_args( 'alphabet_backwards', output, score,
                                        multiplier = 10,
                                        pattern = alphabet_backwards_spec )
    if ok & ( mod.NOT_FOUND + mod.NOT_FUNC ) == 0:
        def gen_cases():
            for i in range(60):
                yield ( random.choice( string.uppercase + string.lowercase ),
                        random.randint(0,26) )
        def aback( last_letter = 'Z', length = 26 ):
            return "".join( map( lambda i: chr(ord(last_letter)-i), range(length) ) )
        def aback_alt( last_letter = 'Z', length = 26 ):
            a = 'A'
            if last_letter.lower() == last_letter:
                a = 'a'
            return aback( last_letter, 
                          min( length, ord(last_letter) - ord(a) + 1 ) )
        best_out = ""
        best_score = 0.0
        for eval in [(aback,''),(aback_alt,'(alternate)')]:
            outp, sc = check_utils.check_func(
                mod.alphabet_backwards, gen_cases(), 
                check_utils.gen_evaluator( eval[0] ),
                "testing"+eval[1], 0.0, multiplier = 2.0 )
            if sc >= best_score:
                best_out = outp
                best_score = sc
        output += best_out
        score += best_score
        output += "\n"
            
    
    output += check_utils.check_func_key()
    
    return ((float(score)/float(max_score))*score_multiplier, output )

def a5b(dir):
    file, dispfile, score_multiplier, output = get_start( dir, 1.0, "" )
    if file == None:
        return ( score_multiplier, output )
    score_multiplier, output = comments_message( file, dispfile,
                                                 score_multiplier, output,
                                                 penalty = 0.10 )
    max_score = 115
    score = 0
    #return 0,"NO OUTPUT"
    def rand_drawitem( min_turn = 1, max_turn = 180,
                       min_dist = 1, max_dist = 100 ):
        return (random.choice(['R','L']),
                random.uniform(min_turn,max_turn),
                random.uniform(min_dist,max_dist))
    def rand_drawlist():
        for i in range(1,20):
            yield rand_drawitem()
    
    mod = check_utils.ModuleWrapper( file )
    sol = check_utils.ModuleWrapper( 'repositories/solutions/a5/start.py', name="solutions" )

    def from_to_xy( drawitem ):
        try:
            print drawitem
            return mod.from_xy(mod.to_xy(drawitem))
        except BaseException, e:
            print e
            raise

    def check_drawitem( case, val ):
        return check_utils.compare_vals( sol.to_xy(*case[0]), sol.to_xy(val) )
    #print map(lambda n: (rand_drawitem(),), range(30))
    mod.add_args_check( 'draw',
                       pattern = ArgSpec( ['turtle','drawlist'], 
                                          None, None, [] ) )
    mod.add_args_check( 'to_xy',
                       pattern = ArgSpec( ['draw'],None,None,[] ) )
    mod.add_func_test('to_xy', 'Circular checks', function = from_to_xy,
                      cases = map(lambda n: tuple([rand_drawitem()]),
                                  range(30)),
                      evaluator = check_drawitem )
    mod.add_func_test('to_xy', 'Extended Angles', function = from_to_xy,
                      cases = map(lambda n: tuple([rand_drawitem(1,360)]),
                                  range(15)),
                      evaluator = check_drawitem )
    mod.add_func_test('to_xy', 'Crazy Angles', function = from_to_xy,
                      cases = map(lambda n: tuple([rand_drawitem(-720,720)]),
                                  range(30)),
                      evaluator = check_drawitem )
    mod.add_args_check( 'from_xy',
                       pattern = ArgSpec( ['coords'],None,None,[] ) )
    mod.add_args_check( 'scale',
                       pattern = ArgSpec( ['factor','drawlist'],
                                          None,None,[] ) )
    mod.add_func_test( 'scale', 'Basic',
                       map(lambda n: (random.uniform(0.25,7), list(rand_drawlist())),
                           range(30)),
                       check_utils.gen_evaluator( sol.scale ) )
    mod.add_args_check( 'polygon',
                       pattern = ArgSpec( ['n','len'], None, None, [] ) )
    #mod.add_func_test( 'polygon', 'Basic',
    #                   map(lambda n: (random.randrange(3,16), random.uniform(4,176)),
    #                       range(30)),
    #                   check_utils.gen_evaluator( sol.polygon ) )
    mod.add_args_check( 'add_drawitems',
                       pattern = ArgSpec( ['a','b'], None, None, [] ) )
    mod.add_args_check( 'simplify',
                       pattern = ArgSpec( 
            ['min_distance','max_combinations','drawlist'],
            None, None, [] ) )
    mod.add_args_check( 'zigzag',
                       pattern = ArgSpec(
            ['item','angle_variance','length_variance'],
            None, None, [] ) )
    mod.add_args_check( 'noisify',
                        pattern = ArgSpec(
            ['min_distance','angle_variance','length_variance','drawlist'],
            None, None, [] ) )

    output,score = mod.run_func_checks( output, score )

    return ((float(score)/float(max_score))*score_multiplier, output )

def a7(dir):
    file, dispfile, score_multiplier, output = get_start( dir, 1.0, "" )
    if file == None:
        return ( score_multiplier, output )
    score_multiplier, output = comments_message( file, dispfile,
                                                 score_multiplier, output,
                                                 penalty = 0.10 )
    max_score = 117
    score = 0
    print file
    mod = check_utils.ModuleWrapper( file )
    sol = check_utils.ModuleWrapper( 'repositories/solutions/a7/start.py', name = 'solution' )

    def rand_thing(i=0,kind=None,noNest=False):
        typegens = {
            'short' : lambda: random.randrange(-32767,32767),
            'bits'  : lambda: random.getrandbits(64),
            'int'   : lambda: random.randint(0,2**32),
            'string': lambda: "".join(random.sample(string.printable,
                                                    random.randrange(3,20))),
            'list'  : lambda: map( lambda x: rand_thing(noNest=True),
                                   range(random.randrange(5,15)) ),
            'dict'  : lambda: dict( map( lambda x: (rand_thing(kind='string'),
                                                    rand_thing(noNest=True)),
                                         range(random.randrange(3,7)) ) )
            }
        if kind == None:
            if noNest:
                klist = ['short','bits','int','string']
            else:
                klist = typegens.keys()
            kind = random.choice(klist)
        return typegens[kind]()

    def rand_word():
        return "".join(random.sample(string.letters,random.randrange(3,11)))
    
    def rand_wordlist():
        return map( lambda x: rand_word(), range(random.randrange(5,50)) )

    def rand_wordlists(n):
        return map( lambda x: rand_wordlist(), range(n) )

    def build_and_lookup_fn(m):
        print m
        def fn( word_lists, lookup_list ):
            word_lists = copy.deepcopy(word_lists)
            lookup_list = copy.deepcopy(lookup_list)
            wl1 = word_lists.pop()
            try:
                ll = m.build_letter_lookup( wl1 )
            except:
                ll = m.build_letter_lookup( wl1, {} )
            
            while len(word_lists) > 0:
                ll = m.build_letter_lookup( word_lists.pop(), ll )
            #now do lookups:
            return map( lambda w: set(m.lookup_letters( w, ll )),
                        lookup_list )
        return fn

    bnl_mod = build_and_lookup_fn(mod)
    bnl_sol = build_and_lookup_fn(sol)

    def mk_bnl_tupleval(n):
        def bnl_tupleval(i):
            if i == 0:
                return rand_wordlists(n)
            else:
                return rand_wordlist()
        return bnl_tupleval
    

    mod.add_args_check( 'lookup_letters',
                        pattern = ArgSpec( ['word','letter_lookup'],
                                           None, None, [] ) )
    mod.add_args_check( 'build_letter_lookup',
                        pattern = ArgSpec( ['words','letter_lookup'],
                                           None, None, [{}] ) )
    mod.add_func_test( 'build_letter_lookup','Single wordlist',
                       check_utils.random_tuple_generator( mk_bnl_tupleval(1), 25, 2 ),
                       check_utils.gen_evaluator( bnl_sol ), function = bnl_mod )
    mod.add_func_test( 'build_letter_lookup','Cumulative wordlists',
                       check_utils.random_tuple_generator( mk_bnl_tupleval(5), 25, 2 ),
                       check_utils.gen_evaluator( bnl_sol ), function = bnl_mod )
    mod.add_args_check( 'multiply_anything',
                        pattern = ArgSpec( ['a','b'],None,None,[] ) )
    mod.add_func_test( 'multiply_anything','Integers',
                       check_utils.random_tuple_generator( lambda: random.randint(-1000,1000),
                                                           25, 2 ),
                       check_utils.gen_evaluator( lambda x,y: x*y ) )
    mod.add_args_check( 'explode', min_args = 1 )
    err_types = set()
    if hasattr(mod,'explode'):
        explode_spec = inspect.getargspec( mod.getattr_raw('explode') )
        print "explode_spec: ", explode_spec
        min_args = len(explode_spec.args or []) - len(explode_spec.defaults or [])
        max_args = len(explode_spec.args or [])
        def test_explode(*args,**varargs):
            try:
                mod.explode(*args,**varargs)
            except check_utils.WrappedError, w:
                err_types.add(w.type.__name__)
                return 1.0
            except BaseException, e:
                err_types.add(type(e).__name__)
                return 1.0
            else:
                return 0.0
        mod.add_func_test( 'explode', 'Explosions',
                           check_utils.random_tuple_generator( lambda: rand_thing(), 25,
                                                   min_length = min_args,
                                                   max_length = max_args ),
                           lambda c,v: v, function = test_explode )
                                                   
    output,score = mod.run_func_checks( output, score )
    print err_types
    if len(err_types) > 4:
        et_score = (len(err_types) - 4)*4
        output += "explode() got {0} different exceptions: +{1}\n".format(
            len(err_types), et_score )
        score += et_score
        
    return ((float(score)/float(max_score))*score_multiplier, output )

def rand_nest( maxd = 3, depth = 0, kind=None ):
    typegens = {
        'int' : lambda: random.randrange(1000),
        'string' : lambda: "".join(random.sample(string.letters,
                                                 random.randrange(1,5)) ),
        'list' : lambda: map( lambda x: rand_nest( maxd, depth + 1 ),
                              range(random.randrange(10)) ),
        'dict' : lambda: dict( map( lambda x: (rand_nest( kind="string" ),
                                               rand_nest( maxd, depth + 1 )),
                                    range(random.randrange(2)) ) ),
        'set' : lambda: set( map( lambda x: rand_nest( kind=("string","int") ),
                                  range(random.randrange(10) ) ) )
        }
    if kind == None:
        if depth == maxd:
            klist = ['string','int']
        elif depth == 0:
            klist = ['list','dict']
        else:
            klist = typegens.keys()
    elif type(kind) == tuple:
        klist = list(kind)
    else:
        klist = [kind]
    kind = random.choice(klist)
    return typegens[kind]()

def a8(dir):
    file, dispfile, score_multiplier, output = get_start( dir, 1.0, "" )
    if file == None:
        return ( score_multiplier, output )
    score_multiplier, output = comments_message( file, dispfile,
                                                 score_multiplier, output,
                                                 penalty = 0.10 )
    max_score = 155
    score = 0
    mod = check_utils.ModuleWrapper( file )
    sol = check_utils.ModuleWrapper( 'repositories/solutions/a8/start.py', name="solutions" )

    mod.add_args_check( 'collapse',
                        pattern = ArgSpec( ['x'],None,None,None ) )
    mod.add_func_test( 'collapse', 'Nested Structures',
                        check_utils.random_tuple_generator( lambda: rand_nest(),
                                                            50, 1 ),
                        check_utils.gen_evaluator( sol.collapse ) )
    mod.add_args_check( 'edit_list',
                        pattern = ArgSpec( ['t','f'],None,None,None ) )
    def el_tup(i,choices=None):
        t = choices
        if t == None:
            t = range(10) * 3
        if i == 0:
            ret = random.sample(t,random.randrange(min(3,len(t)),min(20,len(t)+1)))
            #print ret
            return ret
        elif choices != None:
            return random.choice(t)
        elif i == 1:
            #print "func1"
            return lambda x: [x] * ( x if type(x) == int else 2 )
        else:
            #print "func2"
            return lambda x: [] if type(x) == int and x%2 == 0 else [x]
    
    mod.add_func_test( 'edit_list', 'Expand',
                       check_utils.random_tuple_generator(lambda i: el_tup(i), 25, 2),
                       check_utils.gen_evaluator( sol.edit_list ) )
    mod.add_func_test( 'edit_list', 'Remove Even',
                        check_utils.random_tuple_generator(lambda i: el_tup(i*2),
                                                           25, 2),
                        check_utils.gen_evaluator( sol.edit_list ) )
    mod.add_args_check( 'remove_from_list',
                        pattern = ArgSpec( ['t','x'],None,None,None ) )
    mod.add_func_test( 'remove_from_list', 'Integers',
                       check_utils.random_tuple_generator(
                           lambda i: el_tup(i,range(20)), 25, 2),
                       check_utils.gen_evaluator( sol.remove_from_list ) )
    mod.add_func_test( 'remove_from_list', 'Characters',
                       check_utils.random_tuple_generator(
                           lambda i: el_tup(i,string.uppercase), 25, 2),
                       check_utils.gen_evaluator( sol.remove_from_list ) )
    output,score = mod.run_func_checks( output, score )

    return ((float(score)/float(max_score))*score_multiplier, output )

def a9(dir):
    file, dispfile, score_multiplier, output = \
        get_start( dir, 1.0, "", "PLANNING", lambda f: re.search( "^[A-Z]+$|([Pp][Ll][Aa][Nn])", f) )
    f = open( file )
    lines = f.readlines()
    score = 1.0
    if len(lines) < 5:
        output += "Less than 5 lines in PLANNING.  Did you take this seriosly?"
        score -= 0.2 * ( 5 - len(lines) )
    output += "***Begin***\n" + "".join( lines ) + "***End***\n"
    return (score*score_multiplier, output)
        

if __name__ == '__main__':
    score,results =  a2( 'repositories/solutions/a2' )
    print results
    print "score: ", score
