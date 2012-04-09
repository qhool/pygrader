import StringIO
import random
import re
import sys
import traceback
import inspect
import imp
import os
import os.path
import collections
from compare import compare_vals, isiter, isdict
from copy import deepcopy

class WrappedError( BaseException ):
    def __init__(self):
        self.type, self.value, self.traceback = sys.exc_info()
    def __str__(self):
        #the slice cuts off the check_utils line in traceback:
        return "---".join( traceback.format_exception( self.type, self.value, 
                                                       self.traceback )[1:] )

class WrappedExit( WrappedError ):
    def __init__(self, sys_exit, stderr = None, *args, **varargs ):
        super(WrappedError,self).__init__( *args, **varargs )
        self.code = sys_exit.code
        self.stderr = stderr
    def __str__(self):
        ret = "Program tried to exit with value {0}".format( self.code )
        if self.stderr != None:
            ret += ":\n" + self.stderr.rstrip() + "\n"
        return ret

class WrappedErrSimple( WrappedError ):
    def __init__(self,err):
        self.err = err
    def __str__(self):
        return str(self.err)


def alphabet():
    return "".join( map(chr, range(ord('a'), ord('z')+1)) )

def randomword(min_len,max_len,chars=None):
    wordlen = random.randint( min_len, max_len )
    return "".join( map( lambda x: random.choice(chars or alphabet()), 
                          range(wordlen) ) )

def listdir_recurse( dir ):
    ret = []
    for root, dirs, files in os.walk( dir ):
        for f in files:
            ret.append( os.path.relpath( os.path.join( root, f ), dir ) )
    return ret

def choose_file( dir, fname, file_filter = None ):
    if file_filter == None:
        file_filter = lambda f: re.search( '\.py$', f ) 
    ( head, dispdir ) = os.path.split( dir )
    if os.path.exists( os.path.join( dir, fname ) ):
        found = True
        file = fname
    else:
        allfiles = listdir_recurse(dir)
        possibles = filter( file_filter, 
                            listdir_recurse(dir) )
        if len(possibles) < 1:
            #try files without .py:
            possibles = allfiles
        if len(possibles) < 1:
            return ( False, None, None )
        print "start.py not found.  Other files present: "
        for i in range(len(possibles)):
            print "[{0}] {1}".format( i, possibles[i] )
        try:
            pnum = int(raw_input("Enter number of file, return for none: "))
        except:
            return ( False, None, None )
        found = False
        file = possibles[pnum]
    return ( found, os.path.join( dir, file ), dispdir + '/' + file )

def count_lines( filename ):
    if filename == None or not os.path.isfile( filename ):
        return (0,0,0)
    f = open( filename, 'r' )
    #we use a simple state-machine to parse comments,
    #including [M]ulti[L]ine [S]trings used as comments
    #(where no other code precedes the start of the MLS)
    LINE_START = 0
    NORMAL = 1
    STRING_START = 2
    STRING = 3
    ESCAPE = 4
    MULTSTR = 5 #multiline string
    MULTSTR_P = 6 #if a string char is encountered in STRING_START state
    CONTINUATION = 7
    STRING_CHAR = None #set to "'''" or '"""'

    NORM_START = set([LINE_START,NORMAL])
    CODE_STATES = set([NORMAL, STRING])
    QUOTE_CHARS = set(['"',"'"])
    WHITESPACE_CHARS = set([" ","\t"])

    comment_lines = 0
    code_lines = 0
    blank_lines = 0
    multstr_end_count = 0
    multstr_is_comment = False
    state = LINE_START

    for line in f.readlines():
        line = line.rstrip('\n')
        if len(line) == 0:
            blank_lines += 1
        else:
            line_has_code = False
            for c in line:
                if state in NORM_START:
                    if c == '#': #a comment
                        comment_lines += 1
                        break
                    elif c in QUOTE_CHARS:
                        state = STRING_START
                        string_char = c
                    elif not c in WHITESPACE_CHARS:
                        state = NORMAL
                    elif c == '\\':
                        state = CONTINUATION
                elif state == CONTINUATION:
                    state = NORMAL
                elif state == STRING_START:
                    if c == string_char:
                        state = MULTSTR_P
                    elif c == '\\':
                        state = ESCAPE
                    else:
                        state = STRING
                elif state == MULTSTR_P:
                    if c == string_char:
                        state = MULTSTR
                        multstr_is_comment = not line_has_code
                    else:
                        state = NORMAL
                elif state == STRING:
                    if c == string_char:
                        state = NORMAL
                    elif c == '\\':
                        state = ESCAPE
                elif state == ESCAPE:
                    state = STRING
                elif state == MULTSTR:
                    if c == string_char:
                        multstr_end_count += 1
                        if multstr_end_count >= 3:
                            state = NORMAL
                    else:
                        multstr_end_count = 0
                if state == NORMAL:
                    line_has_code = True
            #line has ended, decide what state to begin new line
            if state == ESCAPE:
                state = STRING
            elif state == CONTINUATION:
                state = NORMAL
            elif state == MULTSTR:
                #MULTSTR continues to next line
                if multstr_is_comment:
                    comment_lines += 1
                else:
                    line_has_code = True
            elif state == LINE_START:
                blank_lines += 1
            else:
                state = LINE_START
            if line_has_code:
                code_lines += 1
    f.close()
    return (code_lines, comment_lines, blank_lines)
                

def comment_ratio( filename ):
    code_lines, comment_lines, blank_lines = count_lines( filename )
    if comment_lines == 0:
        return 0.0
    elif code_lines == 0:
        return 1.0
    else:
        return float(comment_lines)/float(code_lines)

class IORedir():
    def __init__( self, input = "\n" * 100 ):
        #replace sys.std* with stringio, save old handles
        self.sys_stdin = sys.stdin
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr
        self.sio_in = StringIO.StringIO( input )
        self.sio_out = StringIO.StringIO()
        self.sio_err = StringIO.StringIO()
        sys.stdin = self.sio_in
        sys.stdout = self.sio_out
        sys.stderr = self.sio_err
            
    def restore( self ):
        sys.stdin = self.sys_stdin
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr
        self.out = self.sio_out.getvalue()
        self.err = self.sio_err.getvalue()
        self.sio_in.close()
        self.sio_out.close()
        self.sio_err.close()
        return self.out, self.err

def random_tuple_generator( val_gen, count, length = None, 
                            min_length = None, max_length = None ):
    if length == None and min_length == None and max_length == None :
        raise TypeError( "random_tuple_generator(): length, min_length, or max_length must be given" )
    #if val_gen takes an argument, give it the argument position
    vg = lambda n: val_gen()
    if type(val_gen) == type( lambda: 0 ):
        spec = inspect.getargspec(val_gen)
        if len(spec.args) > 0:
            vg = val_gen
    
    for i in range(count):
        if max_length == None:
            ln = length or min_length
        else:
            ln = random.randint( min_length or 0, max_length )
        yield tuple( map( vg, range(ln) ) )

    
def check_func_key():
    return """Test Key:
   .    Correct
   *    Partial Credit
   x    Incorrect
   X    Exception
"""    

def norm_case( case ):
    args = tuple()
    kwargs = dict()
    if isdict( case ):
        kwargs = case
    elif type(case) == tuple:
        args = case
    elif isiter( case ):
        if 0 < len(case) <= 2 and type(case[0]) == tuple:
            args = case[0]
            if len(case) > 1 and isdict( case[1] ):
                kwargs = case[1]
        else:
            args = case
    else:
        args = [case]
    return [ args, kwargs ]

def gen_evaluator( baseline_func, float_precision = 8, dbg = False ):
    def ev( case, val ):
        baseval = baseline_func( *case[0], **case[1] )
        if dbg:
            print "Case: {0}\n".format(case)
            print "Comparing {0}\n\n\n with \n\n\n{1}".format(baseval, val)
        cmpr = compare_vals( baseval, val, float_precision )
        return cmpr
    return ev

#def gen_evaluator_on( baseline_func, func_on_val, float_precision = 8 ):
#    def ev( case, val ):
#        baseval = baseline_func( *case[0], **case[1] )
#        return compare_vals( baseval, func_on_val(val), float_precision )
#    return ev
        
def check_func( function, cases, evaluator, output, score, 
                multiplier = 1.0, exceptions = None ):
    for case in cases:
        case = norm_case(case)
        evalcase = deepcopy(case)
        try:
            ###print case
            ret = function( *case[0], **case[1] )
        except WrappedError, err:
            output += 'X'
            ##print err
            if exceptions != None:
                exceptions.append( err )
        else:
            val = max(0.0, evaluator( case, ret ))
            if abs(val - 1.0) < 10**-4:
                output += '.'
            elif abs(val) < 10**-4:
                output += 'x'
            else:
                output += '*'
            score += multiplier * val
    return output, score

def wrap_assignment( assignment_file, input = None, 
                     globals_ns = None, locals_ns = None ):
    #redirect standard files:
    iord = IORedir()

    #never use the real locals
    if locals_ns == None:
        locals = {}
    if globals_ns == None:
        globals_ns = globals()
    
    exit_val = None
    try:
        execfile( assignment_file, globals_ns, locals_ns )
    except SystemExit, ex:
        exit_val = ex.code
    except:
        iord.restore()
        raise WrappedError()

    out, err = iord.restore()
 
    return (exit_val,out,err)


ArgsCheckDef = collections.namedtuple('ArgsCheckDef', 
                                      ['name','multiplier',
                                       'min_args','max_args',
                                       'pattern', 'tests' ])

FuncTestDef = collections.namedtuple('FuncTestDef',
                                     ['name','description','multiplier',
                                      'function','cases','evaluator',
                                      'arg_flags_mask', 'arg_flags_val', 
                                      'score_above', 'score_below'])

class ModuleWrapper:
    #arg state flags:
    NOT_FOUND = 1
    NOT_FUNC = 2
    TOO_MANY_ARGS = 4
    TOO_FEW_ARGS = 8
    BAD_ARG_NAMES = 16
    TOO_FEW_DEFAULTS = 32
    BAD_DEFAULTS = 64
    VARARGS_FORBID = 128
    VARARGS_REQD = 256
    VARARGS_NAME = 512
    KWARGS_FORBID = 1024
    KWARGS_REQD = 2048
    KWARGS_NAME = 4096
    NUM_FLAGS = 13
    #flag descriptions:
    arg_flag_desc = { 
        NOT_FOUND: " not present ",
        NOT_FUNC: " not a function ",
        TOO_MANY_ARGS: "Too many args -- limit {max_args}",
        TOO_FEW_ARGS: "Not enough args -- {min_args} needed",
        BAD_ARG_NAMES: "Argument names mismatch",
        TOO_FEW_DEFAULTS: "Not enough defaults",
        BAD_DEFAULTS: "Defaults type/value mismatch",
        VARARGS_FORBID: "Variable length arg not allowed",
        VARARGS_REQD: "Variable length arg (*{args}) required",
        VARARGS_NAME: "Variable length arg should be '*{args}'",
        KWARGS_FORBID: "Keywords arg not allowed",
        KWARGS_REQD: "Keywords arg (**{kwargs}) required",
        KWARGS_NAME: "Keywords arg should be '**{kwargs}'"
        }
    

    __wrappable__ = set(["function"])
    def __init__( self, module_file, name = 'start', input = None ):
        iord = IORedir()
        try:
            sys.path.append( os.path.dirname( module_file ) )
            self.wrapped = imp.load_source( name, module_file )
            self.func_checks = {}
            self.func_check_seq = []
            sys.path.pop()
        except SystemExit, ex:
            out, err = iord.restore()
            raise WrappedExit( ex, err )
        except:
            iord.restore()
            raise WrappedError()
        self.out, self.err = iord.restore()
    
    def getattr_raw(self, name):
        try:
            return getattr(self.wrapped, name)
        except AttributeError:
            return None

    def add_args_check( self, name, multiplier = 1.0,
                        min_args = None, max_args = None, 
                        pattern = None ):
        self.func_checks[name] = ArgsCheckDef( name, multiplier,
                                               min_args, max_args, pattern,
                                               [] )
        self.func_check_seq.append(self.func_checks[name])

    def add_func_test( self, name, description,
                       cases = None, evaluator = None,
                       multiplier = 1.0,
                       function = None, 
                       arg_flags_mask = NOT_FOUND + NOT_FUNC, 
                       arg_flags_value = 0,
                       score_above = None,
                       score_below = None ):
        #print "AFT: ", name, description, type(cases)
        if not self.func_checks.has_key(name):
            self.add_args_check( name, 0, max( map(len,cases) ) )
        if function == None:
            function = getattr( self, name )
        self.func_checks[name].tests.append( 
            FuncTestDef( name = name, description = description, multiplier = multiplier,
                         function = function, cases = cases, evaluator = evaluator,
                         arg_flags_mask = arg_flags_mask, arg_flags_val = arg_flags_value,
                         score_above = score_above, score_below = score_below ) )

    def run_func_checks( self, output = "", current_score = 0 ):
        for fchk in self.func_check_seq:
            args_ok, output, func_score = self.check_args( 
                fchk.name, output, 0, fchk.multiplier,
                fchk.min_args, fchk.max_args, fchk.pattern )
            first_test = True
            tests_tot = 0.0
            for tst in fchk.tests:
                 if first_test:
                     output += "Testing:\n"
                     first_test = False
                 output += "\t{0}: ".format(tst.description)
                 test_score = 0.0
                 if ( tst.score_above <= func_score and 
                     func_score <= (tst.score_below or func_score) and
                     args_ok & tst.arg_flags_mask == tst.arg_flags_val ):
                     output, test_score = check_func( 
                        tst.function, tst.cases, tst.evaluator,
                        output, test_score, tst.multiplier )
                 else:
                     output += "...skipped."
                 output += " ({0})\n".format(test_score)
                 tests_tot += test_score
            output += "  Tests total: {0}\n".format(tests_tot)
            current_score += func_score + tests_tot
        return output, current_score
                       

    def check_args(self, name, output = "",
                   current_score = 0, multiplier = 1,
                   min_args = None, max_args = None, 
                   pattern = None ):
        def deftbool( val, default ):
            if type(val) == type(True):
                return default
            else:
                return val

        output += name
        fn = self.getattr_raw( name )
        state = 0
        points_total = 1
        if fn == None:
            state += self.NOT_FOUND
        elif not type(fn).__name__ in self.__wrappable__:
            state += self.NOT_FUNC
        else:
            if ( max_args or min_args ) != None:
                points_total += 1
            for x in pattern or []:
                if type(x) == type([]):
                    points_total += 2
                elif x != None:
                    points_total += 1
            argspec = inspect.getargspec(fn)
            output += inspect.formatargspec( *argspec )
            if pattern != None and pattern.args != None:
                if max_args == None:
                    max_args = len(pattern.args)
                if min_args == None:
                    min_args = len(pattern.args)
            if max_args != None:
                if len(argspec.args) > max_args:
                    state |= self.TOO_MANY_ARGS
            if min_args != None:
                if ( len(argspec.args) < min_args and
                     ( max_args != None or argspec.varargs == None ) ):
                     state |= self.TOO_FEW_ARGS
            if pattern != None:
                if pattern.args != None and len(pattern.args) > 0:
                    for i in range(len(pattern.args)):
                        if len(argspec.args) <= i or \
                                argspec.args[i] != pattern.args[i]:
                            state |= self.BAD_ARG_NAMES
                if pattern.defaults != None and len(pattern.defaults) > 0:
                    adefs = list(argspec.defaults or [])
                    pdefs = list(pattern.defaults)
                    while len(pdefs) > 0:
                        p = pdefs.pop()
                        if len(adefs) == 0:
                            state |= self.TOO_FEW_DEFAULTS
                            break
                        a = adefs.pop()
                        if not isinstance(a, type(p)) or a != p:
                             state |= self.BAD_DEFAULTS
                for attr in ['varargs','keywords']:
                    patn = getattr(pattern,attr)
                    spec = getattr(argspec,attr)
                    if patn == None:
                        continue
                    if attr == 'varargs':
                        forbid_statev = self.VARARGS_FORBID
                        reqd_statev = self.VARARGS_REQD
                        name_statev = self.VARARGS_NAME
                    else:
                        forbid_statev = self.KWARGS_FORBID
                        reqd_statev = self.KWARGS_REQD
                        name_statev = self.KWARGS_NAME
                    if patn == False: 
                        if spec != None:
                            state |= forbid_statev
                    elif patn == True:
                        if spec == None:
                            state |= reqd_statev
                    else:
                        if spec == None:
                            state |= reqd_statev
                        #check that the arg name matches:
                        if spec != patn:
                            state |= name_statev

            if state != 0:
                print "Here 1"
                msglist = map( lambda i: self.arg_flag_desc[2**i], 
                               filter( lambda i: state&2**i > 0,
                                       range(self.NUM_FLAGS) ) )
                disp_vargs = disp_kwargs = ""
                print "here 2"
                if ( pattern != None and ( pattern.args != None or 
                                           pattern.varargs != None or
                                           pattern.kwargs != None ) ):
                        disp_vargs = deftbool( pattern.varargs, 'args' )
                        disp_kwargs = deftbool( pattern.keywords, 'kwargs' )
                        msg = "sample argument list: " 
                        msg += inspect.formatargspec( 
                            pattern.args, disp_vargs,
                            disp_kwargs, 
                            pattern.defaults )
                        msglist.append( msg )
                output += "\n    " + "\n    ".join(msglist).replace('{}','{{}}').format(
                    min_args = min_args, max_args = max_args, 
                    args = disp_vargs, kwargs = disp_kwargs,
                    placeholder = 1) + "\n"
                print "here 4"

            points = points_total - sum( map( lambda i: (state>>i)%2, 
                                              range(self.NUM_FLAGS) ) )
            output += "  {points} out of {total}\n".format(
                points = points, total = points_total )
            return ( state, output, current_score + 
                     multiplier * float(points)/float(points_total) )

    def __getattr__(self, name):
        try:
            attr = getattr(self.wrapped, name)
        except AttributeError, ae:
            raise WrappedErrSimple( ae )
        if type( attr ).__name__ in self.__wrappable__:
            def wrap(*args, **kwargs):
                iord = IORedir()
                try:
                    ret = attr( *args, **kwargs )
                except SystemExit, ex:
                    out, err = iord.restore()
                    raise WrappedExit( ex, err )
                except:
                    self.out, self.err = iord.restore()
                    raise WrappedError()
                self.out, self.err = iord.restore()
                return ret
            return wrap
        else:
            return attr
        
