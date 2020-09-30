#!/usr/bin/env python3
from configparser import ConfigParser
from pathlib import Path
import argparse
import sys
import logging
import subprocess
import time


LAST_UPDATE_FILE = Path("/var/tmp/gitupdater.lock")


def setup_logging(verbose=False):
    logging.addLevelName(logging.ERROR, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(logging.WARNING, "\033[1;33m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
    level = getattr(logging, 'DEBUG' if verbose else 'INFO')
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )


def parse_interval_sec(string):
    units = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }

    for suffix, value in units.items():
        if string.endswith(suffix):
            prefix = float(string.split(suffix)[0])
            return int(prefix * value)


class GitUpdater:
    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.load_default()
        for section in config.sections():
            section_dict = dict(config[section])
            if section_dict:
                logging.debug(f"[{section}]\n{section_dict}")
            self.process_section(config[section])

    def load_default(self):
        update_interval = parse_interval_sec(self.config["DEFAULT"].get("update_interval", "5m"))
        if not LAST_UPDATE_FILE.exists():
            LAST_UPDATE_FILE.touch()
        else:
            last_date = LAST_UPDATE_FILE.stat().st_mtime
            elapsed = time.time() - last_date
            if elapsed < update_interval and not self.args.create:
                logging.debug(f"Only {int(elapsed)}s elapsed, not attempting update before {update_interval}s")
                sys.exit(0)
            else:
                LAST_UPDATE_FILE.touch()

    def process_section(self, section):
        git_path = Path(section["path"]).expanduser()
        if not git_path.exists() or not self.git_folder_is_repo(git_path):
            if not args.create:
                logging.warning(f"Path {git_path} does not exist, run with --create to checkout (missing folders will be created)")
            else:
                self.git_checkout(section["url"], git_path)
        else:
            if section.getboolean("auto_update", False):
                if self.git_has_changes(git_path, self.config["DEFAULT"].getboolean("ignore_untracked_files", False)):
                    logging.warning(f"Path {git_path} has uncommited changes, skipping")
                else:
                    self.git_pull(git_path)

    def git_folder_is_repo(self, path):
        cmd = f"git -C {path} rev-parse"
        try:
            self.run_cmd(cmd, is_safe=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def git_pull(self, path):
        logging.debug(f"Updating {path}")
        cmd = f"git -C {path} pull --rebase"
        if self.run_cmd(cmd) != "Already up to date.":
            logging.info(f"{path} updated")

    def git_checkout(self, git_url, path):
        cmd = f"git clone {git_url} {path}"

        if not self.args.dry_run and not path.is_dir():
            logging.debug(f"Creating path {path}")
            path.mkdir(parents=True)
        else:
            logging.info(f"Dry run: not creating path {path}")

        logging.info(f"Checking out {git_url} into {path}")
        self.run_cmd(cmd)

    def git_has_changes(self, path, ignore_untracked_files=False):
        cmd = f"git -C {path} status --porcelain"
        if ignore_untracked_files:
            cmd += " --untracked-files=no"
        output = self.run_cmd(cmd, is_safe=True)
        if output:
            return True

    def run_cmd(self, cmd, is_safe=False):
        cmd = f"LANG=C {cmd}"
        if not self.args.dry_run or is_safe:
            logging.debug(f"Running {cmd}")
            if not self.args.verbose:
                output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            else:
                output = subprocess.check_output(cmd, shell=True, text=True)
            return output.strip()
        else:
            logging.info(f"Dry run: not running {cmd}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "--config",
        type=str,
        help='Path to alternate config file; defaults to ~/.config/gitupdater and any file in ~/.config/gitupdater.d/'
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="set verbosity to DEBUG",
        action="store_true"
    )

    parser.add_argument(
        "-d",
        "--dry-run",
        help="Do not run any command",
        action="store_true"
    )

    parser.add_argument(
        "--create",
        help="Checkout new repos if needed",
        action="store_true"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    home = Path.home()
    config_files = args.config or [home / ".config/gitupdater"] + list(home.glob(".config/gitupdater.d/*"))

    if args.verbose:
        logging.debug(f"Sourcing config file(s) {config_files}")

    config = ConfigParser()

    config.read(config_files)
    gitupdater = GitUpdater(args, config)
