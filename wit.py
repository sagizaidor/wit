# upload 177
import datetime
import filecmp
import logging
import os
import random
import shutil
import sys

from matplotlib import pyplot as plt


class WaitingForCommitError(Exception):
    pass


def wit_dir_not_found():
    print('.wit directory not found. Please call init first.')


def log(err):
    logging.basicConfig(filename='wit.log', level=logging.DEBUG)
    logging.debug(err)


def init():
    path = os.getcwd()
    dirs = ['.wit', 'images', 'staging_area']
    try:
        for directory in dirs:
            path = os.path.join(path, directory)
            os.mkdir(path)
    except FileExistsError as err:
        log(err)
    else:
        activate_branch('master')


def find_drive_dir():
    drive = os.path.splitdrive(os.getcwd())
    return os.path.join(drive[0], os.path.sep)


def find_wit_dir():
    path = os.getcwd()
    running = True
    while running:
        if path == find_drive_dir():
            running = False
        for dirname in os.listdir(path):
            if dirname == '.wit':
                return os.path.join(path, dirname)
        path = os.path.dirname(path)

    raise FileNotFoundError('There is no .wit folder to this '
                            + 'project, make sure you use init')


def erase_existing_file(dst, err):
    shutil.rmtree(dst)
    log(err)


def copy(src, dst):
    try:
        shutil.copytree(src, dst)
    except FileExistsError as err:
        erase_existing_file(dst, err)
        shutil.copytree(src, dst)
    except NotADirectoryError as err:
        log(err)
        shutil.copy(src, dst)


def add(src):
    dst = os.path.join(find_wit_dir(), 'staging_area', f'{src}')
    copy(src, dst)


def get_HEAD(master=False):
    try:
        with open(
            os.path.join(find_wit_dir(), 'references.txt'), 'r'
        ) as references:
            if not master:
                return references.readline().strip('\n').split('=')[1]
            if master:
                references.readline()
                return references.readline().strip('\n').split('=')[1]
    except FileNotFoundError as err:
        log(err)
        return


def new_commit_txt(massage, merge=False, extra_parent=None):
    parent = get_HEAD()
    if merge:
        parent += f',{extra_parent}'
    return str(
        f'parent={parent}\n'
        + f'date={datetime.datetime.utcnow()}\n'
        + f'massage={massage}')


def get_current_names():
    with open(
            os.path.join(find_wit_dir(), 'references.txt'), 'r'
    ) as references:
        for _ in range(2):
            references.readline()
        names = references.read()
    return names


def write_name(name, commit_id):
    with open(
            os.path.join(find_wit_dir(), 'references.txt'), 'a'
    ) as references:
        references.write(f'\n{name}={commit_id}')


def write_references(commit_id, only_head=False,
                     only_master=False, both=True,
                     name=None, replace_commit_in_branch=None):

    current_names = get_current_names()

    if replace_commit_in_branch is not None:
        branch_id = get_branch(replace_commit_in_branch, by_name=True)
        current_names = current_names.replace(branch_id, commit_id)

    if name is not None:
        write_name(name, commit_id)
        return

    if only_master or only_head:
        both = False
        current_head = get_HEAD()
        current_master = get_HEAD(master=True)

    with open(
            os.path.join(find_wit_dir(), 'references.txt'), 'w'
    ) as references:
        if both:
            references.write(f'HEAD={commit_id}\n')
            references.write(f'master={commit_id}\n')
            references.write(current_names)
        if only_head:
            references.write(f'HEAD={commit_id}\n')
            references.write(f'master={current_master}\n')
            references.write(current_names)
        if only_master:
            references.write(f'HEAD={current_head}\n')
            references.write(f'master={commit_id}\n')
            references.write(current_names)


def commit(massage, merge=False, extra_parent=None):
    commit_id = ''.join(random.choice('1234567890abcdef') for _ in range(40))
    if get_branch(get_active_branch(),
                  by_name=True) == get_HEAD() and not merge:
        branch = get_active_branch()
    else:
        branch = None
    try:
        dst = os.path.join(find_wit_dir(), 'images', commit_id)
    except FileNotFoundError as err:
        log(err)
        wit_dir_not_found()
        return
    with open(f'{dst}.txt', 'w') as f:
        f.write(new_commit_txt(massage, merge, extra_parent))
    src = os.path.join(find_wit_dir(), 'staging_area')
    shutil.copytree(src, dst)
    if get_HEAD() == get_HEAD(master=True) and branch is not None:
        write_references(commit_id, replace_commit_in_branch=branch)
    else:
        write_references(commit_id,
                         only_head=True,
                         replace_commit_in_branch=branch)


def get_changes(dcmp, stat='not committed'):
    if stat == 'committed' or stat == 'untracked':
        for name in dcmp.left_only:
            yield name
    if stat == 'committed' or stat == 'not committed':
        for name in dcmp.diff_files:
            yield name
    for sub_dcmp in dcmp.subdirs.values():
        yield from get_changes(sub_dcmp, stat)


def print_status(
        changes_to_be_committed, changes_not_staged_for_commit,
        untracked_files):
    changes1 = '\n'.join(changes_to_be_committed)
    sep = '-' * 20
    changes2 = '\n'.join(changes_not_staged_for_commit)
    changes3 = '\n'.join(untracked_files)
    print(
        f"Last Committed id: {get_HEAD()}\n"
        + sep
        + f"Changes to be committed:\n{changes1}\n"
        + sep
        + f"Changes not staged for commit:\n{changes2}\n"
        + sep
        + f'untracked files: \n{changes3}\n'
    )


def status(get=False):

    try:
        staging_area = os.path.join(find_wit_dir(), 'staging_area')
    except FileNotFoundError as err:
        log(err)
        return

    last_commit_id = os.path.join(find_wit_dir(), 'images', get_HEAD())
    dcmp = filecmp.dircmp(staging_area, last_commit_id)
    changes_to_be_committed = get_changes(dcmp)
    project_dir = os.path.dirname(find_wit_dir())
    dcmp = filecmp.dircmp(project_dir, staging_area)
    changes_not_staged_for_commit = get_changes(dcmp, stat='not committed')
    untracked_files = get_changes(dcmp, stat='untracked')
    if not get:
        print_status(changes_to_be_committed,
                     changes_not_staged_for_commit,
                     untracked_files)
    if get:
        return(changes_to_be_committed,
               changes_not_staged_for_commit,
               untracked_files)


def copy_from_dir(src, dst):
    for file in os.listdir(src):
        new_src = os.path.join(src, file)
        new_dst = os.path.join(dst, file)
        copy(new_src, new_dst)


def convert_name_to_id(name_or_id):
    id_from_name = get_branch(name_or_id, by_name=True)
    if id_from_name is None:
        return name_or_id
    else:
        return id_from_name


def checkout(commit_id):
    commit_id = convert_name_to_id(commit_id)
    if commit_id == 'master':
        commit_id = get_HEAD(master=True)
    try:
        src = os.path.join(find_wit_dir(), 'images', commit_id)
    except FileNotFoundError as err:
        log(err)
        return
    to_be_committed, not_staged_for_commit, untracked_files = status(get=True)
    if len(list(to_be_committed)) > 0 or len(list(not_staged_for_commit)) > 0:
        raise WaitingForCommitError('There is files waiting for commit.')
    dst = os.path.join(os.path.dirname(find_wit_dir()))
    copy_from_dir(src, dst)
    write_references(commit_id, only_head=True)
    dst = os.path.join(find_wit_dir(), 'staging_area')
    erase_existing_file(dst, None)
    copy_from_dir(src, dst)
    activate_branch(get_branch(commit_id))


def get_parent(commit_id):
    path = os.path.join(find_wit_dir(), 'images', f'{commit_id}.txt')
    try:
        with open(path, 'r') as commit_id_txt:
            parent = commit_id_txt.readline()[7:].strip('\n').split(',')[0]
            return parent
    except FileNotFoundError as err:
        log(err)


def get_current_parents(commit_id='HEAD'):
    if commit_id == 'HEAD':
        commit_id = get_HEAD()
    commits = [commit_id]
    running = True

    while running:
        commit = get_parent(commits[-1])
        if commit is None:
            running = False
        else:
            commits.append(commit)

    return commits


def graph():

    def create_box(name, x, y, previous_an):
        return ax.annotate(name, xy=(x + 0.5, y + 0.5), xycoords=previous_an,
                           xytext=(30, 0), textcoords="offset points",
                           va="bottom", ha="left",
                           size=fontsize,
                           bbox=dict(boxstyle="round", fc="w"),
                           arrowprops=dict(arrowstyle="->"))

    commits = get_current_parents()
    size = len(commits)
    fontsize = 5

    _, ax = plt.subplots()
    ax.plot(size, 1)
    x, y = 0.5, 0.5

    previous_an = ax.annotate(commits[0], xy=(x, y), xycoords="axes points",
                              size=fontsize,
                              bbox=dict(boxstyle="round", fc="w"))

    for commit in commits[1:]:
        new_an = create_box(commit, x, y, previous_an)
        previous_an = new_an

    plt.show()


def get_active_branch():
    with open(
            os.path.join(find_wit_dir(), 'activated.txt'), 'r'
    ) as activated:
        return activated.read()


def get_branch(commit_id, by_name=False):
    names_list = get_current_names().split('\n')
    for name in names_list:
        branch, c_id = name.split('=')
        if by_name:
            if branch == commit_id:
                return c_id
        if id == commit_id:
            return branch


def activate_branch(NAME):
    with open(
            os.path.join(find_wit_dir(), 'activated.txt'), 'w'
    ) as activated:
        try:
            activated.write(NAME)
        except TypeError as err:
            log(err)
            activated.write('None')


def branch(name):
    NAME = name
    commit_id = get_HEAD()
    write_references(commit_id=commit_id, name=NAME)


def find_common_base(commit1, commit2):
    parents1 = get_current_parents(commit1)
    parents2 = get_current_parents(commit2)
    for parent1 in parents1:
        for parent2 in parents2:
            case1 = parent1 == parent2
            case2 = parent1 != commit1
            case3 = parent2 != commit2
            case4 = parent1 != commit2
            case5 = parent2 != commit1
            if case1 and case2 and case3 and case4 and case5:
                return parent1


def merge(branch_name):
    inputted_branch = convert_name_to_id(branch_name)
    current_branch = get_HEAD()
    common_base = find_common_base(current_branch, inputted_branch)
    if common_base is None:
        print("No common base found")
        return
    branch_path = os.path.join(find_wit_dir(), 'images', inputted_branch)
    base_path = os.path.join(find_wit_dir(), 'images', common_base)
    dcmp = filecmp.dircmp(branch_path, base_path)
    changes = get_changes(dcmp, stat='untracked')
    print(list(changes))
    dst = os.path.join(find_wit_dir(), 'staging_area')
    for file in changes:
        src = os.path.join(branch_path, file)
        dst = os.path.join(find_wit_dir(), 'staging_area')
        copy(src, dst)
    commit(f'merge of {get_branch(current_branch)} and {branch_name}',
           merge=True, extra_parent=inputted_branch)
    activate_branch('HEAD')


if sys.argv[1] == 'init':
    init()

if sys.argv[1] == 'add':
    add(sys.argv[2])

if sys.argv[1] == 'commit':
    try:
        commit(sys.argv[2])
    except IndexError:
        log('There is no massage given')
        commit('')

if sys.argv[1] == 'status':
    status()

if sys.argv[1] == 'checkout':
    try:
        checkout(sys.argv[2])
    except WaitingForCommitError as err:
        log(err)

if sys.argv[1] == 'graph':
    try:
        find_wit_dir()
        graph()
    except FileNotFoundError as err:
        log(err)

if sys.argv[1] == 'branch':
    try:
        find_wit_dir()
        branch(sys.argv[2])
    except FileNotFoundError as err:
        log(err)

if sys.argv[1] == 'merge':
    try:
        find_wit_dir()
        merge(sys.argv[2])
    except FileNotFoundError as err:
        log(err)
