#!/usr/bin/env python3
"""
Script to be executed before commiting, to do things fast.

Installation: ln -sr hooks/pre_commit.py .git/hooks/pre-commit

You can pass "--unstaged" to apply the hook on modified but not yet
staged files. This is useful to apply the hook prior staging.

This script is modular: it calls tools only on the staged/unstaged files, not
on all git-tracked files.
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional


def _git_diff(staged_or_modified: bool, extension: str) -> List[str]:
    """
    Args:
        extension: the extension of files considered, such as "py" or "ml"
        staged_or_modified: Whether to consider staged files (True)
                            or modified ones (False)
    Returns: A list of relevant versioned files that are staged or modified
    """
    git_cmd = ["git", "diff"]
    if staged_or_modified:
        git_cmd += ["--cached"]
    git_cmd += ["--name-only", "--diff-filter=ACMR", "*." + extension]
    git_diff_result = subprocess.run(
        git_cmd, check=True, stdout=subprocess.PIPE, universal_newlines=True
    )
    # The comprehension filters empty lines
    return [x for x in git_diff_result.stdout.split("\n") if x]


def _call_tool(files: List[str], staged_or_modified: bool, cmd: list) -> int:
    """
    Args:
        files: The files on which to call a tool (which is expected
               to modify these files)
        staged_or_modified: Whether staged files are considered (True)
                            or modified ones (False)
        cmd: The command to call the considered tool. The path to a
             given file is appended to it before executing it.
    Returns:
        The maximum of return codes of calls to the considered tool on `files`
    """
    if staged_or_modified:
        # If we're dealing with staged files, we don't want to format
        # if the file has unstaged modifications; because
        # adding (in git) the file after having formatted would stage
        # those modifications
        git_cmd = ["git", "diff", "--name-only"]
        modified_files_result = subprocess.run(
            git_cmd, check=True, stdout=subprocess.PIPE, universal_newlines=True
        )
        trimmed_files = [
            x for x in files if x not in modified_files_result.stdout.split("\n")
        ]
        excluded = [x for x in files if x not in trimmed_files]
        if excluded:
            print(
                "Some files are not considered because"
                " they have unstaged modifications."
                "\nModifying them and readding them would stage unwanted"
                " modifications\nConcerned files:"
            )
            for exclude in excluded:
                print("  " + exclude)
        files = trimmed_files
    return_code = 0
    for file_ in files:
        tool_cmd = cmd + [file_]
        print(" ".join(tool_cmd))
        subprocess.run(tool_cmd, check=True)
        if staged_or_modified:
            # Readd file, so that formatting makes it to the commit
            # This is safe, because of the previous check having
            # no unstaged modification. Hence adding it only stages
            # formatting changes
            #
            # On another topic, we have no way to know if the tool did
            # a modification. Hence we're always readding. If we had
            # this information, we would be able to avoid these calls.
            git_cmd = ["git", "add", file_]
            print(" ".join(git_cmd))
            subprocess.run(git_cmd, check=True)
    return return_code


def _run_cmd(cmd: List[str], cwd: Optional[str] = None, check: bool = False) -> int:
    """
    Args:
        cmd: The command to execute
        cwd: The working directory where to execute the command
        check: whether to fail with an Exception if the command fails
    Returns:
        The command's return code
    """
    prefix = f"{cwd}> " if cwd else ""
    print(f'{prefix}{" ".join(cmd)}')
    return subprocess.run(cmd, check=check, cwd=cwd).returncode


def main() -> int:
    """The main"""
    staged = "--unstaged" not in sys.argv
    adjective = "staged" if staged else "modified"

    return_code = 0

    relevant_ml_files = _git_diff(staged, "ml")
    if relevant_ml_files:
        # <THIS IS AN EXAMPLE CALL, REPLACE ME!>
        ocamlformat_rc = _call_tool(
            relevant_ml_files, staged, ["ocamlformat", "--inplace"]
        )
        return_code = max(return_code, ocamlformat_rc)
    else:
        print(f"No {adjective} *.ml relevant file found: nothing to format")

    return return_code


if __name__ == "__main__":
    sys.exit(main())
