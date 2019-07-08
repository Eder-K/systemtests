"""Script for system testing preCICE with docker and comparing output.

This script builds a docker image for an system test of preCICE.
It starts a container of the builded image and copys the output generated by the
simulation within the test to the host.
The output is compared to a reference.
It passes if files are equal, else it raises an exception.

Example:
    System test of-of and use local preCICE image

        $ python system_testing.py -s of-of -l
"""

import argparse, filecmp, os, shutil, sys
import common, docker
from common import ccall, get_test_variants, filter_tests

def build(systest, tag, branch, local, force_rebuild):
    """ Builds a docker image for systest. """
    baseimage_name = "precice-" + tag + "-" + branch + ":latest"
    test_tag = systest + "-" +  tag + "-" + branch
    if local:
        docker.build_image(tag = test_tag,
                           build_args = {"from" : docker.get_namespace() + baseimage_name},
                           force_rebuild = force_rebuild)
    else:
        docker.build_image(tag = test_tag,
                           build_args = {"from" :
                               'precice/' + baseimage_name},
                           force_rebuild = force_rebuild)

def run(systest, tag, branch):
    """ Runs (create a container from an image) the specified systest. """
    test_tag = docker.get_namespace() + systest + "-" + tag + "-" + branch
    ccall("docker run -it -d --name " + test_tag + " " + test_tag)
    shutil.rmtree("Output", ignore_errors=True)
    ccall("docker cp " + test_tag + ":Output . ")


class IncorrectOutput(Exception):
    def __init__(self, diff_files, left_only, right_only):
        self.diff_files = diff_files
        self.left_only = left_only
        self.right_only = right_only

    def __str__(self):
        s  = "Output files do not match reference\n"
        s += "Files differing               : " + str(self.diff_files) + "\n"
        s += "Files only in reference (left): " + str(self.left_only) + "\n"
        s += "Files only in output(right)   : " + str(self.right_only)
        return s



def comparison(pathToRef, pathToOutput):
    """Compares two directories

    Args:
        pathToRef (str): Path to the reference files.
        pathToOutput (str): Path to the output files.

    Raises:
        Exception: Raises IncorrectOutput when output differs from reference.
    """
    ret = common.get_diff_files(filecmp.dircmp(pathToRef, pathToOutput, ignore = [".gitkeep"]))
    if ret[0] or ret[1] or ret[2]:
        raise IncorrectOutput(*ret)



def build_run_compare(test, tag, branch, local_precice, force_rebuild):
    """ Runs and compares test, using precice branch. """
    dirname = "/Test_" + test
    test_basename = test.split('.')[0]
    with common.chdir(os.getcwd() + dirname):
        # Build
        build(test_basename, tag, branch, local_precice, force_rebuild)
        run(test_basename, tag, branch)
        # Preparing string for path
        pathToRef = os.path.join(os.getcwd(), "referenceOutput")
        pathToOutput = os.path.join(os.getcwd(), "Output")
        # Comparing
        comparison(pathToRef, pathToOutput)


if __name__ == "__main__":
    # Parsing flags
    parser = argparse.ArgumentParser(description='Build local.')
    parser.add_argument('-l', '--local', action='store_true', help="use local preCICE image (default: use remote image)")
    parser.add_argument('-s', '--systemtest', type=str, help="choose system tests you want to use",
                        choices = common.get_tests())
    parser.add_argument('-b', '--branch', help="preCICE branch to use", default = "develop")
    parser.add_argument('-f', '--force_rebuild', nargs='+', help="Force rebuild of variable parts of docker image",
                        default = [], choices  = ["precice", "tests"])
    parser.add_argument('--base', type=str,help="Base preCICE image to use", default= "Ubuntu1604.home")
    args = parser.parse_args()
    test = str(args.systemtest) + '.' + str(args.base)
    # check if there is specialized dir for this version
    test_name = args.systemtest
    all_derived_tests = get_test_variants(test_name)
    test = filter_tests(all_derived_tests, 'Dockerfile.'+args.base)
    if len(test) != 1:
        raise Exception("Could not determine test to run!")
    else:
        test = test[0]
    tag = args.base.lower()
    build_run_compare(test, tag, args.branch.lower(), args.local, args.force_rebuild)
