from assignment import Assignment
from StringIO import StringIO
import repo
import os
import sys
import re
import hashlib
import imp
import string
import shutil

REPLACE = 1
UPDATE = 2
NEW_ONLY = 3

def check_work( args ):
    students = repo.get_student_list(ssh=args.sshlist)
    if args.student != None and len(args.student) > 0:
        student_filter = set(args.student)
        students = filter( lambda s: s in student_filter, students )

    for assignment_id in args.assignment:
        a = Assignment(assignment_id, pull=args.pull, verbose=args.verbose)
        print a.name
        for s in students:
            if args.dry_run:
                print "\n" + "-"*10
            feedback_fname = 'feedback/{adir}/{std}.txt'.format(
                adir = a.dir, std = s )
            if args.action == NEW_ONLY and os.path.isfile( feedback_fname ):
                print "{0} already exists, skipping".format( feedback_fname )
                continue
            print s + ": ",
            (state, submissions) = a.check_submission( s )
            if submissions == None or not args.dry_run:
                print Assignment.state_description( state )
            if submissions != None:
                comments = ""
                if os.path.isfile( feedback_fname ) and args.action == UPDATE:
                     old_fb = open( feedback_fname, 'r' )
                     comments_started = False
                     for line in old_fb:
                         if comments_started:
                             comments += line
                         elif re.match( '---COMMENTS---', line ):
                             comments_started = True
                     old_fb.close()
                if args.dry_run:
                    feedback = StringIO()
                else:
                    feedback = open( 'feedback/{adir}/{std}.txt'.format(
                            adir = a.dir, std = s ), 'w' )
                feedback.write( Assignment.state_description( state ) + "\n" )
                for sub in submissions:
                    feedback.write( str(sub) + "\n" )
                    score, results = sub.evaluate()
                    feedback.write( results + "\n" )
                    feedback.write( "score: {0}\n".format( score ) )
                    break
                if not args.dry_run or len(comments) > 0:
                    feedback.write( "---COMMENTS---\n" ) 
                if len(comments) > 0:
                    feedback.write( comments )
                elif not args.dry_run:
                    #gives an easy way to find files where comments not written
                    feedback.write( "#NEW# -- delete this line when done\n" )
                if args.dry_run:
                    print feedback.getvalue()
                    print "-="*25 + "-" 
                feedback.close

def loop_feedback( args, per_assignment, per_feedback, pull=False ):
    if hasattr( args, 'student' ) and args.student != None and len(args.student) > 0:
        student_filter = set(args.student)
    else:
        student_filter = None
    for assignment_id in args.assignment:
        a = Assignment(assignment_id, pull=pull, verbose=args.verbose)
        fbdir = 'feedback/{adir}'.format( adir = a.dir )
        per_a_ret = per_assignment( a, fbdir ) if per_assignment != None else True
        if per_a_ret != None:
            for fname in filter( lambda fn: re.search( "\.txt$", fn ), os.listdir( fbdir ) ):
                student, ext = os.path.splitext( fname )
                if student_filter != None:
                    if not student in student_filter:
                        continue
                per_feedback( a, per_a_ret, fbdir, fname, student )
    
def boilerplate( args ):
    def open_boilerplate( a, fbdir ):
        bplate = os.path.join( fbdir, "boilerplate.py" )
        if not os.path.isfile( bplate ):
            print "Assignment {n} has no boilerplate.py".format( n = a.name )
            return None
        return imp.load_source( 'boilerplate', bplate )

    def add_boilerplate( a, bp, fbdir, fname, student ):
        f = open( os.path.join( fbdir, fname ), "r+" )
        txt = f.read()
        tmpl = string.Template( txt )
        new_txt = tmpl.substitute( vars(bp) )
        if args.dry_run:
            print fname + ": "
            print new_txt
            print "=" * 40
        else:
            print fname
            f.seek(0)
            f.write(new_txt)
            f.close()

    loop_feedback( args, open_boilerplate, add_boilerplate )

def post( args ):
    def post_fb( a, true, fbdir, fname, student ):
        state, submissions = a.check_submission( student )
        cur_sub = submissions.pop()
        fb_src = os.path.join( fbdir, fname )
        fb_dest = os.path.join( cur_sub.dir, 'FEEDBACK' )
        do_push = False
        actn_desc = 'Update'
        f = open( fb_src )
        feedback_txt = f.read()
        f.close()
        if re.search( r"#NEW#", feedback_txt ):
            print "{sf} is still #NEW#".format( 
                sf = os.path.relpath( fb_src ) )
        #a solitary dollar sign suggests boilerplate 
        #which needs expanding
        elif re.search( r"(?<!\$)\$(?!\$)", feedback_txt ):
            print "{sf} appears to have unreplaced boilerplate code[s]."\
                .format( sf = os.path.relpath( fb_src ) )        
        elif not os.path.isfile( fb_dest ):
            do_push = True
            actn_desc = 'Add'
        elif args.update:
            def hashf( fn ):
                f = open( fn, 'r' )
                hasher = hashlib.md5()
                hasher.update( f.read() )
                f.close()
                digest = hasher.hexdigest()
                if args.verbose:
                    print digest, fn
                return digest
            if hashf( fb_src ) != hashf( fb_dest ):
                if ( not args.no_check_date and
                     os.path.getmtime( fb_src ) < os.path.getmtime( fb_dest ) ):
                    print "{d} is newer than {s}".format( 
                        s = os.path.relpath(fb_src), 
                        d = os.path.relpath(fb_dest) )
                else:
                    do_push = True
        if do_push:
            if args.dry_run:
                print "{0} --> {1}".format( fb_src, os.path.relpath(fb_dest) )
            else:
                if args.verbose:
                    print "copy {0} to {1}".format( fb_src, os.path.relpath(fb_dest) )
                shutil.copyfile( fb_src, fb_dest )
                def flushp( str ):
                    print str,
                    sys.stdout.flush()
                print student + ":",
                def gitstep( cmd ):
                    flushp( cmd + "..." )
                    return getattr(git,cmd)

                git_output = ""
                git = cur_sub.repo.git
                try:
                    git_output += gitstep( 'add')(fb_dest)
                    git_output += gitstep( 'commit' )(
                        m = '{act} feedback for {t}'.format( 
                            t = a.title, act = actn_desc ) )
                    git_output += gitstep( 'push' )()
                    flushp( "done." )
                    print ""
                except:
                    print git_output
                    raise
                if args.verbose:
                    print git_output

    loop_feedback( args, None, post_fb, pull = True )
