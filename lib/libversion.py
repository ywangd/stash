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


def _parse_version(vs):
    """
    Parse a version string, e.g. '2!3.0.1.rc2.dev3'
    :param vs: version to parse
    :type vs: str
    :return: a dict containing the fragments about the version
    :rtype: dict
    """
    # NOTE: the below code may be a bit messy, because it was rewritten multiple times and then repurposed from a sort-function to a parsing-function
    # version scheme (PEP440): [N!]N(.N)*[{a|b|rc}N][.postN][.devN]
    # convert to lowercase, since all versions must be case insenstive (PEP440)
    e = vs.lower()
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
        postrnstr = rtstr[rtstr.find("post") + 4:]
        postrnres = re.search("[0-9]*", postrnstr)
        if postrnres is None or postrnres.end() == 0:
            # PEP440: implicit post version 0
            subpriority = 0
        else:
            subpriority = int(postrnstr[:postrnres.end()])
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
    # extract dev release information
    devr = re.search("\\.?dev[0-9]*", e)
    if devr is None:
        isdev = False
        devnum = 0
    else:
        isdev = True
        devns = e[devr.start() + 4:]  # 4: 1 for '.'; 3 for 'dev'
        if len(devns) == 0:
            devnum = 0
        else:
            devnum = int(devns)
    return {
        "epoch": epoch,
        "versiontuple": tuple(verparts),
        "rtype": rtype,
        "subversion": rsubpriority,
        "postrelease": (subpriority if is_post else None),
        "devrelease": (devnum if isdev else None),
        }


def sort_versions(versionlist):
    """
    Return a list containing the versions in versionlist, starting with the highest version.
    :param versionlist: list of versions to sort
    :type versionlist: list of str
    :return: the sorted list
    :rtype: list of str
    """
    return sorted(versionlist, key=lambda s: Version.parse(s) if isinstance(s, str) else s, reverse=True)


class Version(object):
    """
    This class represents a version. It is mainly used for version comparsion.
    """
    TYPE_NORMAL = None
    TYPE_ALPHA = "a"
    TYPE_BETA = "b"
    TYPE_RELEASE_CANDIDATE = "rc"

    RELEASE_TYPE_PRIORITIES = {
        # priority of a release type. greate => higher priority
        TYPE_NORMAL: 3,   # no release type
        TYPE_ALPHA: 0,    # alpha post release
        TYPE_BETA: 1,    # beta post release
        TYPE_RELEASE_CANDIDATE: 2,   # release candidate
    }

    def __init__(self, epoch=0, versiontuple=(), rtype=None, subversion=0, postrelease=None, devrelease=None):
        assert isinstance(epoch, int)
        assert isinstance(versiontuple, tuple)
        assert isinstance(rtype, str) or rtype is None
        assert isinstance(subversion, int)
        assert isinstance(postrelease, int) or postrelease is None
        assert isinstance(devrelease, int) or devrelease is None
        self.epoch = epoch
        self.versiontuple = versiontuple
        self.rtype = rtype
        self.subversion = subversion
        self.postrelease = postrelease
        self.devrelease = devrelease

    @classmethod
    def parse(cls, s):
        """
        Parse a versionstring and return a Version() of it.
        :param s: string to parse
        :type s: str
        :return: a Version() instance describing the parsed string
        :rtype: Version
        """
        if isinstance(s, cls):
            # s is already a Version
            return s
        parsed = _parse_version(s)
        return Version(**parsed)

    @property
    def is_postrelease(self):
        """whether this version is a postrelease or not"""
        return self.postrelease is not None

    @property
    def is_devrelease(self):
        """whether this version is a devrelease or not"""
        return self.devrelease is not None

    def _get_sortkey(self):
        """
        Return a value which can be used to compare two versions.
        Sort order:
        1. epoch
        2. release version
        3. postrelease > release > prerelease
        4. postrelease#
        5. non-dev > dev
        6. dev#

        :return: a value which can be used for comparing this version to another version
        :rtype: tuple
        """
        rpriority = self.RELEASE_TYPE_PRIORITIES.get(self.rtype, 0)
        return (self.epoch, self.versiontuple, rpriority, self.subversion, self.is_postrelease, self.postrelease, not self.is_devrelease, self.devrelease)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._get_sortkey() == other._get_sortkey()
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return self._get_sortkey() > other._get_sortkey()
        else:
            return True

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self._get_sortkey() < other._get_sortkey()
        else:
            return False

    def __ge__(self, other):
        if isinstance(other, self.__class__):
            return self._get_sortkey() >= other._get_sortkey()
        else:
            return False

    def __le__(self, other):
        if isinstance(other, self.__class__):
            return self._get_sortkey() <= other._get_sortkey()
        else:
            return False



    def __str__(self):
        """return a string representation of this version"""
        version = ".".join([str(e) for e in self.versiontuple])  # base version
        # epoch
        if self.epoch > 0:
            version = str(self.epoch) + "!" + version
        # release type
        if self.rtype is not None:
            version += "." + self.rtype
            if self.subversion > 0:
                version += str(self.subversion)
        # postrelease
        if self.is_postrelease:
            version += ".post"
            if self.postrelease > 0:
                version += str(self.postrelease)
        # devrelease
        if self.is_devrelease:
            version += ".dev"
            if self.devrelease > 0:
                version += str(self.devrelease)
        # done
        return version


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
        PAREN = lambda x: '(' + x + ')'
        version_cmp = PAREN('?:' + '|'.join(('<=', '<', '!=', '>=', '>', '~=', '==')))
        name_end_res = re.search(version_cmp, requirement)
        if name_end_res is None:
            return requirement, None
        name_end = name_end_res.start()
        name, specs_s = requirement[:name_end], requirement[name_end:]
        splitted = specs_s.split(",")
        specs = []
        for vs in splitted:
            cmp_end = re.search(version_cmp, vs).end()
            c, v = vs[:cmp_end], vs[cmp_end:]
            specs.append((c, v))
        version = VersionSpecifier(specs)
        return name, version

    def match(self, version):
        """
        Check if version is allowed by the version specifiers.
        :param version: version to check
        :type version: str
        :return: whether the version is allowed or not
        :rtype: boolean
        """
        # return all([op(Version.parse(version), Version.parse(ver)) for op, ver in self.specs])
        matches = True
        for op, ver in self.specs:
            try:
                vi = Version.parse(version)
                evi = Version.parse(ver)
            except:
                # warning: wildcard except!
                # fallback to old, string-based comparsion
                if not op(version, ver):
                    matches = False
            else:
                if not op(vi, evi):
                    matches = False
        return matches
