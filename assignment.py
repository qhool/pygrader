import config
import repo
from check_utils import WrappedError
import datetime
import re
import os.path
import traceback

class AssignmentNotFoundError(Exception):
    def __init__(self,ident):
        self.ident = ident 
    def __str__(self):
        return "Assignment '{0}' not found!".format( self.ident )

class Submission:
    @staticmethod
    def late_days( deadline, actual ):
        if deadline == None or actual == None:
            return None
        def convdt( d ):
            if re.search( 'Commit', type(d).__name__ ):
                return repo.commit_datetime( d )
            else:
                return d
        tdelta = convdt(actual) - convdt(deadline)
        return tdelta.days + ( float(tdelta.seconds) + 
                               float(tdelta.microseconds)/1000000 )/(60*60*24)

    def __init__( self, assignment, commit, first = False, dir = None ):
        self.assignment = assignment
        self.commit = commit
        self.repo = commit.repo
        self.first = first
        self.late = self.late_days( assignment.due_date, self.commit )
        self.dead = self.late_days( assignment.drop_dead_date, self.commit )
        self.dir = os.path.join( self.commit.repo.working_tree_dir, 
                                 dir or self.assignment.dir )

    def __str__( self ):
        changedesc = 'Added' if self.first else 'Revised'
        if self.dead > 0:
            days = self.dead
            deadline_desc = 'drop-dead'
        else:
            days = self.late
            deadline_desc = 'due'

        rel = 'before' if days < 0 else 'after'

        return "{0} {1:.2f} days {2} {3} date: {4}"\
            .format( changedesc, abs(days), rel, deadline_desc, self.commit )

    def evaluate( self ):
        f = self.assignment.get_test_func()
        self.repo.git.checkout(str(self.commit))
        if f == None:
            return (None, "No eval func defined\n")
        try:
            return f( self.dir )
        #this lets exceptions in eval func to still raise to top:
        except WrappedError, err:
            self.repo.heads.master.checkout()
            return (0.0, "Got error executing assignment:\n" + str(err) )
        except:
            self.repo.heads.master.checkout()
            raise
        self.repo.heads.master.checkout()

class Assignment:
    EMPTY = 0
    MISSING = 1
    MALFORMED = 2
    COMPLETE = 4

    @classmethod
    def state_description( cls, state ):
        if state == cls.EMPTY:
            return "Empty Repository"
        elif state == cls.MISSING:
            return "Assignment not submitted"
        elif state == cls.MALFORMED:
            return "Assignment incomplete or malformed"
        elif state == cls.COMPLETE:
            return "Assignment submitted"

    @staticmethod
    def fmt_dir( spec ):
        if hasattr( spec, 'dir' ):
            return spec.dir
        else:
            return getattr(config.assignments, 'dir_pattern', '{name}')\
                .format( number = spec.number,
                         name = Assignment.fmt_name(spec) )

    @staticmethod
    def fmt_name( spec ):
        if hasattr( spec, 'name' ):
            return spec.name
        else:
            return getattr(config.assignments, 'name_pattern', 'a{number}')\
                .format( number = spec.number )

    def __init__( self, spec, pull=True, verbose=False ):
        self.verbose = verbose
        #tabs arg for repo.find_?_commit() funcs
        self.r_tabs = "" if self.verbose else None
        try:
            spec = int(spec)
        except:
            None
        if type(spec) == type(int()):
            for a in config.assignments.list:
                if a.number == spec:
                    self.spec = a
                    break
        elif type(spec) == type(str()):
            for a in config.assignments.list:
                if spec in set([Assignment.fmt_dir( a ),
                                Assignment.fmt_name( a )]):
                    self.spec = a
                    break
        elif type(spec) == type(config.assignments.list[0]):
            self.spec = spec
        if self.spec == None:
            raise AssignmentNotFoundError( spec )
        self.pull = pull

        for k in self.spec.iterkeys():
            setattr(self,k,self.spec[k])
        self.number = self.spec.number
        self.title = self.spec.get('title',
                                   "Assignment #{0}".format(self.number))
        self.due_date = self.spec.due_date
        self.dir = Assignment.fmt_dir( self.spec )
        self.name = Assignment.fmt_name( self.spec )

        self.required_files = []
        for r in self.spec.get('required_files',
                               config.assignments.get('required_files',[])):
            self.required_files.append( r.format( number = self.number,
                                                  title = self.title,
                                                  dir = self.dir ) )
        self.check_files = self.required_files
        if len( self.check_files ) == 0:
            self.check_files = [ self.dir ]

        #find solutions commit:
        solrepo = repo.get_solutions_repo(self.pull)
        self.solutions_commit = self.first_full_commit( solrepo )

        if self.spec.has_key('drop_dead_date'):
            self.drop_dead_date = self.spec.drop_dead_date
        else:
            #use date when the solution was posted:
            self.drop_dead_date = repo.commit_datetime(self.solutions_commit)

        if self.verbose:
            for attr in [ 'number', 'name', 'title', 'dir',
                          'due_date', 'drop_dead_date' ]:
                print attr.replace( "_", " " ) + ": " +\
                    str( getattr( self, attr ) )
            print "required files:\n\t" + "\n\t".join( self.check_files )


    #find first commit where all required files have been added
    def first_full_commit( self, repository ):
        latest_commit = None
        for r in self.required_files:
            cmt = repo.find_first_commit( repository, r, tabs = self.r_tabs )
            if cmt == None:
                return None
            elif latest_commit == None or \
                    cmt.committed_date > latest_commit.committed_date:
                latest_commit = cmt
        return latest_commit

    def last_commit( self, repository, before = None ):
        return repo.find_last_commit( repository, self.dir, before, 
                                      tabs = self.r_tabs  )

    def check_submission( self, student ):
        stud_repo = repo.get_repo( student, self.pull )
        if stud_repo == None:
            return ( self.EMPTY, None )
        state = self.COMPLETE
        first = self.first_full_commit( stud_repo )
        sub_dir = self.dir
        if first == None:
            #either a required file is missing, or the dir is mis-named
            dir_matches = []
            first = repo.find_first_commit( stud_repo, '(?i)' + self.dir,
                                            matches = dir_matches,
                                            tabs = self.r_tabs )
            if first == None:
                return ( self.MISSING, None )
            else:
                state = self.MALFORMED
                sub_dir = dir_matches[0]

        first_date = repo.commit_datetime( first )
        submissions = []
        def add_subm( commit ):
            if len(submissions) == 0 or \
                    submissions[len(submissions)-1].commit != commit:
                submissions.append( Submission( self, commit, 
                                                len(submissions) == 0,
                                                dir = sub_dir ) )

        for dd in [self.due_date, self.drop_dead_date, None]:
            if dd == None or first_date < dd:
                add_subm( repo.find_last_commit( stud_repo, sub_dir, dd,
                                                 tabs = self.r_tabs ) )

        return (state, submissions)

    def get_test_func( self ):
        mod = getattr(self,'test_module',
                      config.assignments.get('test_module'))
        func = getattr(self,'test_func', self.name)
        if mod != None and func != None:
            m = __import__(mod)
            return getattr(m,func)
        else:
            return None
        
        
#sols = repo.get_solutions_repo()
#students = repo.get_student_list()

#for a_cfg in config.assignments.list:
#    a_dir = config.assignments.all.dir_pattern.format(number=a_cfg.number)
#    print a_dir


if __name__ == '__main__':
    a = Assignment('a2', pull=False)
    print a.title
