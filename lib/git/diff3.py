# ============================================================================
# Copyright (C) 1988, 1989, 1992, 1993, 1994 Free Software Foundation, Inc.
# Copyright (c) 2011-2012 University of Pennsylvania
# Copyright (c) 2013-2014 Andreas Schuh
# All rights reserved.
# ============================================================================

"""

    @file  diff3.py
    @brief Three-way file comparison algorithm.

    This is a line-by-line translation of the Text::Diff3 Perl module version
    0.10 written by MIZUTANI Tociyuki <tociyuki@gmail.com>.

    The Text::Diff3 Perl module in turn was based on the diff3 program:

    Three way file comparison program (diff3) for Project GNU.
    Copyright (C) 1988, 1989, 1992, 1993, 1994 Free Software Foundation, Inc.
    Written by Randy Smith

    The two-way file comparison procedure was based on the article:
    P. Heckel. ``A technique for isolating differences between files.''
    Communications of the ACM, Vol. 21, No. 4, page 264, April 1978.

    jsb: added newlines for conflict markers
"""

from operator import xor


# ----------------------------------------------------------------------------
def diff3(yourtext, origtext, theirtext):
    """Three-way diff based on the GNU diff3.c by R. Smith.

    @param [in] yourtext   Array of lines of your text.
    @param [in] origtext   Array of lines of original text.
    @param [in] theirtext  Array of lines of their text.

    @returns Array of tuples containing diff results. The tuples consist of
             (cmd, loA, hiA, loB, hiB), where cmd is either one of
             '0', '1', '2', or 'A'.

    """
    # diff result => [(cmd, loA, hiA, loB, hiB), ...]
    d2 = (diff(origtext, yourtext), diff(origtext, theirtext))
    d3 = []
    r3 = [None, 0, 0, 0, 0, 0, 0]
    while d2[0] or d2[1]:
        # find a continual range in origtext lo2..hi2
        # changed by yourtext or by theirtext.
        #
        #     d2[0]        222    222222222
        #  origtext     ...L!!!!!!!!!!!!!!!!!!!!H...
        #     d2[1]          222222   22  2222222
        r2 = ([], [])
        if not d2[0]:
            i = 1
        else:
            if not d2[1]:
                i = 0
            else:
                if d2[0][0][1] <= d2[1][0][1]:
                    i = 0
                else:
                    i = 1
        j = i
        k = xor(i, 1)
        hi = d2[j][0][2]
        r2[j].append(d2[j].pop(0))
        while d2[k] and d2[k][0][1] <= hi + 1:
            hi_k = d2[k][0][2]
            r2[k].append(d2[k].pop(0))
            if hi < hi_k:
                hi = hi_k
                j = k
                k = xor(k, 1)
        lo2 = r2[i][0][1]
        hi2 = r2[j][-1][2]
        # take the corresponding ranges in yourtext lo0..hi0
        # and in theirtext lo1..hi1.
        #
        #   yourtext     ..L!!!!!!!!!!!!!!!!!!!!!!!!!!!!H...
        #      d2[0]        222    222222222
        #   origtext     ...00!1111!000!!00!111111...
        #      d2[1]          222222   22  2222222
        #  theirtext          ...L!!!!!!!!!!!!!!!!H...
        if r2[0]:
            lo0 = r2[0][0][3] - r2[0][0][1] + lo2
            hi0 = r2[0][-1][4] - r2[0][-1][2] + hi2
        else:
            lo0 = r3[2] - r3[6] + lo2
            hi0 = r3[2] - r3[6] + hi2
        if r2[1]:
            lo1 = r2[1][0][3] - r2[1][0][1] + lo2
            hi1 = r2[1][-1][4] - r2[1][-1][2] + hi2
        else:
            lo1 = r3[4] - r3[6] + lo2
            hi1 = r3[4] - r3[6] + hi2
        # detect type of changes
        if not r2[0]:
            cmd = '1'
        elif not r2[1]:
            cmd = '0'
        elif hi0 - lo0 != hi1 - lo1:
            cmd = 'A'
        else:
            cmd = '2'
            for d in range(0, hi0 - lo0 + 1):
                (i0, i1) = (lo0 + d - 1, lo1 + d - 1)
                ok0 = (0 <= i0 and i0 < len(yourtext))
                ok1 = (0 <= i1 and i1 < len(theirtext))
                if xor(ok0, ok1) or (ok0 and yourtext[i0] != theirtext[i1]):
                    cmd = 'A'
                    break
        d3.append((cmd, lo0, hi0, lo1, hi1, lo2, hi2))
    return d3

# ----------------------------------------------------------------------------


def merge(yourtext, origtext, theirtext):
    res = {'conflict': 0, 'body': []}
    d3 = diff3(yourtext, origtext, theirtext)
    text3 = (yourtext, theirtext, origtext)
    i2 = 1
    for r3 in d3:
        for lineno in range(i2, r3[5]):
            res['body'].append(text3[2][lineno - 1])
        if r3[0] == '0':
            for lineno in range(r3[1], r3[2] + 1):
                res['body'].append(text3[0][lineno - 1])
        elif r3[0] != 'A':
            for lineno in range(r3[3], r3[4] + 1):
                res['body'].append(text3[1][lineno - 1])
        else:
            res = _conflict_range(text3, r3, res)
        i2 = r3[6] + 1
    for lineno in range(i2, len(text3[2]) + 1):
        res['body'].append(text3[2][lineno - 1])
    return res

# ----------------------------------------------------------------------------


def _conflict_range(text3, r3, res):
    text_a = []  # their text
    for i in range(r3[3], r3[4] + 1):
        text_a.append(text3[1][i - 1])
    text_b = []  # your text
    for i in range(r3[1], r3[2] + 1):
        text_b.append(text3[0][i - 1])
    d = diff(text_a, text_b)
    if _assoc_range(d, 'c') and r3[5] <= r3[6]:
        res['conflict'] += 1
        res['body'].append('<<<<<<<\n')
        for lineno in range(r3[1], r3[2] + 1):
            res['body'].append(text3[0][lineno - 1])
        res['body'].append('|||||||\n')
        for lineno in range(r3[5], r3[6] + 1):
            res['body'].append(text3[2][lineno - 1])
        res['body'].append('=======\n')
        for lineno in range(r3[3], r3[4] + 1):
            res['body'].append(text3[1][lineno - 1])
        res['body'].append('>>>>>>>\n')
        return res
    ia = 1
    for r2 in d:
        for lineno in range(ia, r2[1]):
            res['body'].append(text_a[lineno - 1])
        if r2[0] == 'c':
            res['conflict'] += 1
            res['body'].append('<<<<<<<\n')
            for lineno in range(r2[3], r2[4] + 1):
                res['body'].append(text_b[lineno - 1])
            res['body'].append('=======\n')
            for lineno in range(r2[1], r2[2] + 1):
                res['body'].append(text_a[lineno - 1])
            res['body'].append('>>>>>>>\n')
        elif r2[0] == 'a':
            for lineno in range(r2[3], r2[4] + 1):
                res['body'].append(text_b[lineno - 1])
        ia = r2[2] + 1
    for lineno in range(ia, len(text_a)):
        res['body'].append(text_a[lineno - 1])
    return res

# ----------------------------------------------------------------------------


def _assoc_range(diff, diff_type):
    for d in diff:
        if d[0] == diff_type:
            return d
    return None

# ----------------------------------------------------------------------------


def _diff_heckel(text_a, text_b):
    """Two-way diff based on the algorithm by P. Heckel.

    @param [in] text_a Array of lines of first text.
    @param [in] text_b Array of lines of second text.

    @returns TODO

    """
    d = []
    uniq = [(len(text_a), len(text_b))]
    (freq, ap, bp) = ({}, {}, {})
    for i in range(len(text_a)):
        s = text_a[i]
        freq[s] = freq.get(s, 0) + 2
        ap[s] = i
    for i in range(len(text_b)):
        s = text_b[i]
        freq[s] = freq.get(s, 0) + 3
        bp[s] = i
    for s, x in freq.items():
        if x == 5:
            uniq.append((ap[s], bp[s]))
    (freq, ap, bp) = ({}, {}, {})
    uniq.sort(key=lambda x: x[0])
    (a1, b1) = (0, 0)
    while a1 < len(text_a) and b1 < len(text_b):
        if text_a[a1] != text_b[b1]:
            break
        a1 += 1
        b1 += 1
    for a_uniq, b_uniq in uniq:
        if a_uniq < a1 or b_uniq < b1:
            continue
        (a0, b0) = (a1, b1)
        (a1, b1) = (a_uniq - 1, b_uniq - 1)
        while a0 <= a1 and b0 <= b1:
            if text_a[a1] != text_b[b1]:
                break
            a1 -= 1
            b1 -= 1
        if a0 <= a1 and b0 <= b1:
            d.append(('c', a0 + 1, a1 + 1, b0 + 1, b1 + 1))
        elif a0 <= a1:
            d.append(('d', a0 + 1, a1 + 1, b0 + 1, b0))
        elif b0 <= b1:
            d.append(('a', a0 + 1, a0, b0 + 1, b1 + 1))
        (a1, b1) = (a_uniq + 1, b_uniq + 1)
        while a1 < len(text_a) and b1 < len(text_b):
            if text_a[a1] != text_b[b1]:
                break
            a1 += 1
            b1 += 1
    return d


# ----------------------------------------------------------------------------
diff = _diff_heckel  # default two-way diff function used by diff3()
