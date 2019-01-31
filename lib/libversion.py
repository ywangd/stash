"""version utilities"""
import re
import operator

def sort_versions(versionlist):
    """
    Return a list containing the versions in versionlist, starting with the highest version.
    :param versionlist: list of versions to sort
    :type versionlist: list of str
    :return: the sorted list
    :rtype: list of str
    """
    def sortf(e):
        """extract the key for the search"""
        splitted = e.split(".")
        ret = []
        for v in splitted:
            # some versions may contain a string
            # in py3, comparsion between int and str is no longer possible :(
            # thus we instead sort by a tuple of (int, str), where str is the non-digt part of the version
            s = re.search("[^0-9]", v)
            if s is None:
                # only numbers
                a, b = int(v), ""
            else:
                # contains non-digits
                i = s.start()
                a, b = v[:i], v[i:]
                if a == "":
                    # sometimes, non-numeric versions are used for dev releases
                    # we should fallback to 0, to give priority to non-dev versions
                    a = 0
                else:
                    a = int(a)
            # ret.append((a, b))
            ret.append(a)  # TODO: replace with above line. There still seem to be some issues with the order of versions containing non-digits.
        return tuple(ret)
    return sorted(versionlist, key=sortf, reverse=True)


class VersionSpecifier(object):
    """
    This class is to represent the versions of a requirement, e.g. pyte==0.4.10.
    """
    OPS = {'<=': operator.le,
    '<': operator.lt,
    '!=': operator.ne,
    '>=': operator.ge,
    '>': operator.gt,
    '==': operator.eq,
    '~=': operator.ge}

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
