"""version utilities"""
import re
import operator


# release type identifier -> release type priority (higher == better)
RELEASE_TYPE_PRIORITIES = {
    None: 4,   # no release type
    "a": 1,    # alpha post release
    "b": 2,    # beta post release
    "rc": 3,   # release candidate
    "post": 5,  # post release
    "dev": 0,   # dev release
}


def sort_versions(versionlist):
    """
    Return a list containing the versions in versionlist, starting with the highest version.
    :param versionlist: list of versions to sort
    :type versionlist: list of str
    :return: the sorted list
    :rtype: list of str
    """
    # version scheme (PEP440): [N!]N(.N)*[{a|b|rc}N][.postN][.devN]
    # order:
    # 1. epoch
    # 2. release version
    # 3. postrelease > release > prerelease
    # 4. postrelease#
    # 5. non-dev > dev
    # 6. dev#
    def sortf(e):
        """extract the key for the search"""
        # convert to lowercase, since all versions must be case insenstive (PEP440)
        e = e.lower()
        # extract information from
        if "!" in e:
            # read epoch
            es = e[:e.find("!")]
            e = e[e.find("!") + 1:]
            epoch = int(es)
        else:
            # default epoch is 0
            epoch = 0
        # parse version tuple
        veis = re.search("[^0-9\\.]", e)
        if veis is None:
            # no non-digits
            vei = len(e)
        else:
            vei = veis.start()
        vstr = e[:vei]
        while vstr.endswith("."):
            # remove trailing '.'
            vstr = vstr[:-1]
        splitted = vstr.split(".")
        verparts = []
        for v in splitted:
            verparts.append(int(v))
        # parse post release
        rtstr = e[vei:]
        if "post" in rtstr:
            try:
                subpriority = int(rtstr[rtstr.find("post") + 4:])
            except ValueError:
                # PEP440: implicit post version 0
                subpriority = 0
            rtstr = rtstr[:rtstr.find("post") - 1]
            is_post = True
        else:
            subpriority = 0
            is_post = False
        # parse release type
        rtype = None
        if len(rtstr) == 0:
            rtype = None
        elif rtstr[0] in ("a", "b"):
            rtype = rtstr[0]
        elif rtstr.startswith("rc"):
            rtype = "rc"
        # parse number of release
        if rtype is None:
            # not needed
            rsubpriority = 0
        else:
            # 1. strip rtype
            rtps = rtstr[len(rtype):]
            # 2. extract until non-digit
            rtpsr = re.search("[0-9]*", rtps)
            if rtpsr is None or rtpsr.end() == 0:
                # no number
                rsubpriority = 0
            else:
                rsubpriority = int(rtps[:rtpsr.end()])
        rpriority = RELEASE_TYPE_PRIORITIES.get(rtype, 0)  # unknown -> be skeptical
        # extract dev release information
        devr = re.search("\\.?dev[0-9]*", rtstr)
        if devr is None:
            isdev = False
            devnum = 0
        else:
            isdev = True
            devns = rtstr[devr.start() + 4:]  # 4: 1 for '.'; 3 for 'dev'
            if len(devns) == 0:
                devnum = 0
            else:
                devnum = int(devns)
        # below is the search key (=value by which the version list will be ordered)
        # comparsion *should* be from i=0 to i=-1
        return (epoch, tuple(verparts), rpriority, rsubpriority, is_post, subpriority, not isdev, devnum)
    return sorted(versionlist, key=sortf, reverse=True)


class VersionSpecifier(object):
    """
    This class is to represent the versions of a requirement, e.g. pyte==0.4.10.
    """
    OPS = {
        '<=': operator.le,
        '<': operator.lt,
        '!=': operator.ne,
        '>=': operator.ge,
        '>': operator.gt,
        '==': operator.eq,
        '~=': operator.ge,
        }

    def __init__(self, version_specs):
        self.specs = [(VersionSpecifier.OPS[op], version) for (op, version) in version_specs]
        self.str = str(version_specs)

    def __str__(self):
        return self.str

    @staticmethod
    def parse_requirement(requirement):
        """
        Factory method to create a VersionSpecifier object from a requirement
        """
        if isinstance(requirement, (list, tuple)):
            if len(requirement) == 1:
                requirement = requirement[0]
            else:
                raise ValueError("Unknown requirement format: " + repr(requirement))
        # remove all whitespaces and '()'
        requirement = requirement.replace(' ', '')
        requirement = requirement.replace("(", "").replace(")", "")
        if requirement.startswith("#"):
            # ignore
            return None, None
        letterOrDigit = r'\w'
        PAREN = lambda x: '(' + x + ')'

        version_cmp = PAREN('?:' + '|'.join(('<=', '<', '!=', '>=', '>', '~=', '==')))
        version_re = PAREN('?:' + '|'.join((letterOrDigit, '-', '_', '\.', '\*', '\+', '\!'))) + '+'
        version_one = PAREN(version_cmp) + PAREN(version_re)
        package_name = '^([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9])'
        parsed = re.findall(package_name + version_one, requirement)

        if not parsed:
            return requirement, None
        name = parsed[0][0]
        reqt = list(zip(*parsed))
        version_specifiers = list(zip(*reqt[1:]))  # ((op,version),(op,version))
        version = VersionSpecifier(version_specifiers)

        return name, version

    def match(self, version):
        """
        Check if version is allowed by the version specifiers.
        :param version: version to check
        :type version: str
        :return: whether the version is allowed or not
        :rtype: boolean
        """
        return all([op(version, ver) for op, ver in self.specs])
