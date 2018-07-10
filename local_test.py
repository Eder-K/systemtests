#!/usr/bin/env python3
"""Script for testing on the local machine.

This script allows to build preCICE with a branch choosen by the user, execute
all or choosen system tests and allows to push the results to the output repository
of preCICE system test.

    Example:
        Example to use preCICE branch "master" and only system tests "of-of" and "su2-ccx":

            $ python local_test.py --branch=master --systemtest of-of su2-ccx
"""

import argparse, os, subprocess
import docker, common
from common import call, ccall
from system_testing import build_run_compare

# Parsing flags
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                 description='Build local.')
parser.add_argument('-b', '--branch', help="choose branch you want to use for preCICE", default = "develop")
parser.add_argument('-s', '--systemtest', nargs='+', help="choose system tests you want to use", default = common.get_tests())
args = parser.parse_args()

if __name__ == "__main__":
    tests = args.systemtest
    
    # Checking for older docker images
    lst1 = docker.get_images()
    if lst1:
        print("Deleting following docker images:", lst1)
        answer = input("\nOk? (yes/no)\n")
        if answer in ["yes", "y"]:
            for x in lst1:
                ccall("docker image rm -f " + x)
        else:
            print("BE CAREFUL!: Not deleting previous images can later lead to problems.\n\n")
            
    # Checking for older docker containers
    lst2 = docker.get_containers()
    if lst2:
        print("Deleting following docker containers:", lst2)
        answer = input("\nOk? (yes/no)\n")
        if answer in ["yes", "y"]:
            for x in lst2:
                ccall("docker container rm -f " + x)
        else:
            print("BE CAREFUL!: Not deleting previous containers can later lead to problems.")

    # Building preCICE
    print("\n\nBuilding preCICE docker image with choosen branch\n\n")
    branch = args.branch
    docker.build_image("precice-" + branch, "Dockerfile.precice", {"branch" : branch})
    # Starting system tests
    failed = []
    success = []
    for test in tests:
        print("\n\nStarting system test %s\n\n" % test)
        try:
            build_run_compare(test, "develop", True)
        except subprocess.CalledProcessError:
            failed.append(test)
        else:
            success.append(test)

    # Results
    print("\n\n\n\n\nLocal build finished.\n")
    if success:
        print("Following system tests succeeded: ")
        print(", ".join(success))
        print('\n')
    if failed:
        print("Following system tests failed: ")
        print(", ".join(failed))
        print('\n')

    # Push
    answer = input("Do you want to push the results (logfiles and possibly output files) to the output repo? (yes/no)\n")
    if answer in ["yes", "y"]:
        for x in success:
            ccall("python push.py --success --test " + x + " --branch " + args.branch)
        for y in failed:
            ccall("python push.py --test " + y + " --branch " + args.branch)