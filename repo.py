import config
import subprocess
from git import *
import re
import operator
from time import *
import datetime
import os

class CommandError(Exception):
    def __init__(self,args,value,stderr):
        self.args = args
        self.value = value
        self.stderr = stderr
    def __str__(self):
        return """Command: {0}
Exited with {1}:
{2}""".format( " ".join(self.args), self.value, self.stderr )



def get_cmd_out(args):
    p = subprocess.Popen( args, stdout = subprocess.PIPE, 
                          stderr = subprocess.PIPE )
    ( out, err ) = p.communicate()
    if p.returncode != 0:
        raise CommandError( args, p.returncode, err )
    return out
         

def get_student_list(ssh=True):
    if ssh:
        ssh_args = [ config.system.ssh, 
                     config.repository.user + '@' + config.repository.host,
                     'ls ' + config.repository.path ]
        out = get_cmd_out( ssh_args ).split("\n")
    else:
        out = filter( lambda d: os.path.isdir(os.path.join('repositories',d)),
                      os.listdir( 'repositories/' ) )

    return set(out).difference( config.repository.exclude, [ '' ] )

def clone_repo(reponame):
    git_args = [ config.system.git, "clone",
                 config.repository.user + '@' + config.repository.host + ':' +
                 config.repository.path + '/' + reponame,
                 'repositories/' + reponame ]
    out = get_cmd_out( git_args )

_repo_cache = dict()        
                 
def get_repo( repo_name, pull = True ):
    if _repo_cache.has_key(repo_name):
        return _repo_cache[repo_name]
    print "get repo for {0}...".format(repo_name),
    try:
        r = Repo('repositories/' + repo_name)
        r.heads.master.checkout()
        if pull:
            print "pulling...",
            r.remote().pull()
    except NoSuchPathError:
        print "cloning...",
        clone_repo(repo_name)
        r = Repo('repositories/' + repo_name)
    except AssertionError, e:
        print "[Assertion: " + str(e) + " ]"
    print "done"
    _repo_cache[repo_name] = r
    return r

def get_solutions_repo(pull = True):
    return get_repo(config.assignments.solutions, pull)

def commit_datetime( commit ):
    if commit == None:
        return None
    else:
        return datetime.datetime.fromtimestamp( commit.committed_date )
    
def pick_gen( pick, filt=None ):
    def picker(a,b):
        if filt != None:
            a = filt(a)
            b = filt(b)
        if b == None:
            return a
        elif a == None:
            return b
        else:
            return pick(a,b)
    return picker

def date_pick_gen( comp, endpoint ):
    endpt = endpoint
    if type(endpoint) == type(datetime.datetime.now()):
        endpt = mktime( endpoint.timetuple() )
    def endpt_filt(a): 
        return a if a != None and comp(endpt,a.committed_date) else None
    def comp_picker(a,b):
        if comp(a.committed_date,b.committed_date):
            return a
        else:
            return b
    return pick_gen( comp_picker, endpt_filt if endpoint != None else None )


def find_commit( head, path_spec, pick, tabs=None, matches = None ):
    headtype = type(head)
    if re.search( 'Repo', type(head).__name__ ):
        if len(head.heads) == 0:
            return None
        head = head.heads.master.commit
    elif re.search( 'Head', type(head).__name__ ):
        head = head.commit
    
    parents = head.parents
    if tabs != None:
        print tabs, head, ": ", ctime(head.committed_date)
    found_commit = None
    if len(parents) == 0:
        parents = [ None ]
    def check_blob_match( blob ):
        f_commit = found_commit
        if tabs != None:
            print tabs, "  ", blob.path
        m = re.search( path_spec, blob.path )
        if m != None:
            f_commit = pick( f_commit, head )
            if type(matches) == type(list()):
                matches.append( m.group() )
        return f_commit
    for p in parents:
        if p == None:
            for b in head.tree.traverse():
                if re.search( 'Blob', type(b).__name__ ):
                    found_commit = check_blob_match( b )
        else:
            diffs = p.diff( head )
            for d in diffs:
                if d.b_blob != None:
                    found_commit = check_blob_match( d.b_blob )

            p_found_commit = \
                find_commit( p, path_spec, pick, 
                             None if tabs == None else tabs + "\t",
                             matches )
        
            found_commit = pick( found_commit, p_found_commit )

    if tabs != None:
        if found_commit == head:
            print tabs, "<-- SELF"
        elif found_commit == None:
            print tabs, "<-- None"
        else:
            print tabs, "<==", found_commit, "/" + ctime(found_commit.committed_date)
    return found_commit

def find_last_commit( head, path_spec, before=None, tabs=None, matches = None ):
    return find_commit( head, path_spec, 
                        date_pick_gen( operator.gt, before ), tabs, matches )

def find_first_commit( head, path_spec, after=None, tabs=None, matches = None ):
    return find_commit( head, path_spec, 
                        date_pick_gen( operator.lt, after ), tabs, matches )

def pull_all():
    students = get_student_list()
    for st in students:
        get_student_repo(st)


if __name__ == '__main__':
    sols = get_repo('tuser')
    cmt = find_last_commit( sols, "test", before=1315319771, tabs="" )
    print cmt, ctime(cmt.committed_date), cmt.committed_date
