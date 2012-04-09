#!/usr/bin/env python
from argparse import ArgumentParser
from cmd_modes import *
from sys import argv
import os.path
me =  os.path.basename(argv[0])
parser = ArgumentParser( usage="%(prog)s [options] MODE [mode_options] ASSIGNMENT [ASSIGNMENT ...]" )
subparsers = parser.add_subparsers( title='Available Modes',
                                    description='use "%(prog)s MODE --help" to get options for MODE')
parser.add_argument( '--student', action='append' )
parser.add_argument( '-v', '--verbose', action='store_true', dest='verbose' )

check_parser = subparsers.add_parser( 
    'check', help='Check assignments & create feedback templates.',
    usage = "FOO!" )
check_parser.add_argument( '--pull', action='store_const', const=True, dest='pull',
                     default = False, help = 'do git pull on repositories' )
check_parser.add_argument( '--ssh-list', action='store_const', const=True, 
                     dest='sshlist', default = False, 
                     help = 'use ssh to get repository list from git server' )
check_parser.add_argument( '--replace', action='store_const', const=REPLACE,
                     dest='action', default = NEW_ONLY )
check_parser.add_argument( '--update', action='store_const', const=UPDATE, 
                     dest='action' )
check_parser.add_argument( '--dry-run', action='store_true' )
check_parser.add_argument( 'assignment', metavar='ASSIGNMENT', nargs = '+'  )

check_parser.set_defaults( func=check_work )


boiler_parser = subparsers.add_parser( 
        'boiler', help='Insert boilerplate comments into feedback.',
        usage = "{0} [-v] [--student STUDENT] boiler [options] ASSIGNMENT [ASSIGNMENT ...]".format(me) )
boiler_parser.add_argument( 'assignment', metavar='ASSIGNMENT', nargs = '+'  )
boiler_parser.add_argument( '--dry-run', action='store_true' )

boiler_parser.set_defaults( func=boilerplate )

post_parser = subparsers.add_parser(
    'post', help='Copy feedback to student dirs, commit & push.',
    usage = "{0} [-v] [--student STUDENT] post [options] ASSIGNMENT [ASSIGNMENT ...]".format(me))
post_parser.add_argument( 'assignment', metavar='ASSIGNMENT', nargs = '+'  )
post_parser.add_argument( '--dry-run', action='store_true' )
post_parser.add_argument( '--update', action='store_true' )
post_parser.add_argument( '--no-check-date', action='store_true' )
post_parser.set_defaults( func=post )

args = parser.parse_args()

args.func(args)
#close stderr to supress the smmap error messages
sys.stderr.close()
