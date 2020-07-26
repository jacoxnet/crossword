import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var, words in self.domains.items():
            for test_word in words.copy():
                if var.length != len(test_word):
                    words.remove(test_word)

    def compare_domain(x, y, xwords, ywords):
        """
        This static method is used to compare the domains of
        two variables that overlap at (x, y). xwords and ywords
        are sets of words for the x and y variables. Returns
        a new set of words for the x variable. Called by 
        revise.
        """
        # go through each word in x domain
        # see if consistent with some word in y domain
        for xword in xwords.copy():
            consistent = False
            if len(xword) < x:
                # too short to be consistent
                continue
            for yword in ywords:
                if len(yword) < y or xword == yword:
                    # too short or same word - not consistent
                    continue
                # now compare overlapping character
                consistent = (xword[x] == yword[y])
                if consistent:
                    # we're done with that xword once we find a 
                    # consistent yword
                    break
            # now we've compared all ywords for the xword
            if not consistent:
                # must remove xword if no ywords were consistent
                xwords.remove(xword)
        return xwords

    
    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        # get overlap if any in x and y
        o = self.crossword.overlaps[x, y]
        if not o:
            # no overlap - can't be inconsistent
            return False
        # else go through each word in x domain
        # see if consistent with some word in y domain
        new_xwords = CrosswordCreator.compare_domain(o[0], o[1], self.domains[x].copy(), 
                                                     self.domains[y])
        revised = (len(new_xwords) != len(self.domains[x]))
        if revised:
            self.domains[x] = new_xwords
        return revised
        

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if not arcs:
            # if empty arcs set, start with all arcs
            # go through each var and add tuple of var with all neighbors
            arcs = set()
            for var in self.crossword.variables:
                arcs = arcs.union(set((var, v) for v in self.crossword.neighbors(var)))
        while len(arcs) != 0:
            (x, y) = arcs.pop()
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                arcs = arcs.union(set((z, x) for z in (self.crossword.neighbors(x) - {y})))
        return True


    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        if self.crossword.variables - set(assignment.keys()) == set():
            return True
        else:
            return False


    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # check if duplicate values (words)
        if len(assignment) != len(set(assignment.values())):
            return False
        # now go through each variable and word in assignment
        for var, word in assignment.items():
            # check length
            if len(word) != var.length:
                return False
            # now see if consistent with neighbors in assignment
            for nvar, nword in assignment.items():
                # evaluate only for other variables in assignment
                if nvar != var:
                    # check if overlap
                    o = self.crossword.overlaps[nvar, var]
                    if o:
                        # if overlap, check specific letters in two words
                        if nword[o[0]] != word[o[1]]:
                            return False
        return True


    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        # neighbors minus vars already assigned
        nb = self.crossword.neighbors(var) - set(assignment.keys())
        # count number of words in neighbor domain ruled out
        # for each word in our domain
        ruled_out = {}
        for our_word in self.domains[var]:
            ruled_out[our_word] = 0
            # go through neighborhood vars
            for nvar in nb:
                # get overlaps for two vars (guaranteed since they're neighbors)
                x, y = self.crossword.overlaps[var, nvar]
                # for each one go through domain words
                for n_word in self.domains[nvar]:
                    # check specific letters in words
                    # if not the same, ruled out +1
                    if our_word[x] != n_word[y]:
                        ruled_out[our_word] += 1
        # when done, sort by ruled_out number and return
        return sorted(self.domains[var], key=lambda word: ruled_out[word])


    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # figure out number of values and degree for ordering
        # vars is all vars minus those in assignment already
        vars = set(v for v in self.crossword.variables) - set(assignment.keys())
        # number of values in domain
        num_vals = {v: len(self.domains[v]) for v in vars}
        # degree of each var
        deg = {v: len(self.crossword.neighbors(v)) for v in vars}
        # sort primary ascending by num_vals and then descending by degree
        s = sorted(sorted(vars, key = lambda d: deg[d], reverse=True), 
                   key=lambda n: num_vals[n])
        return s[0]


    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.
        `assignment` is a mapping from variables (keys) to words (values).
        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            # assign this value to assignment
            assignment[var] = value
            # check consistency of tentative assignment
            if self.consistent(assignment):
                result = self.backtrack(assignment)
                # if result valid return it
                if result:
                    return result
            # not consistent - remove from assignment
            assignment.pop(var)
        # we've tried all in domain, return None
        return None    
        

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
