import sys
from crossword import *
from collections import deque
from copy import deepcopy
from PIL import Image, ImageDraw, ImageFont

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
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
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
        #all_variables = list(self.domains.keys())
        for variable in self.crossword.variables:
            size_match = set()
            for value in self.domains[variable]:
                if len(value) == variable.length:
                    size_match.add(value)
            self.domains[variable] = size_match
            
    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """

        revised = False
        overlap = self.crossword.overlaps[x, y]

        if not overlap:
            return False

        i, j = overlap

        remove = set()
        for word_x in self.domains[x]:
            match_exists = False
            for word_y in self.domains[y]:
                if word_x[i] == word_y[j]:
                    match_exists = True
                    break
            if not match_exists:
                remove.add(word_x)
        
        if remove:
            self.domains[x] -= remove
            revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = deque()
        if arcs is not None:
            queue.extend(arcs)
        else:
            queue.extend(
                (x, y)
                for x in self.crossword.variables
                for y in self.crossword.neighbors(x)
            )

        while queue:
            x, y = queue.pop()
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                for z in self.crossword.neighbors(x) - {y}:
                    queue.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for variable in assignment:
            if not variable in self.crossword.variables:
                return False
        for variable in self.crossword.variables:
            if not variable in assignment:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        
        used_words = set()

        for variable_a, word_a in assignment.items():

            if word_a in used_words:
                return False
            
            if len(word_a) != variable_a.length:
                return False
            
            used_words.add(word_a)

            for variable_b in self.crossword.neighbors(variable_a):
                if variable_b not in assignment:
                    continue

                word_b = assignment[variable_b]
                overlap = self.crossword.overlaps[variable_a, variable_b]

                if not overlap:
                    continue

                i, j = overlap

                if word_a[i] != word_b[j]:
                    return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        degrees = {}

        print("var is ", var)
        print("self.domains is ", self.domains)

        for key in self.domains[var]:
            print("key is ", key)
            degrees[key] = 0
        
        for word_a in self.domains[var]:
            degree = 0
            for variable_b in self.crossword.neighbors(var):
                for word_b in self.domains[variable_b]:
                    overlap = self.crossword.overlaps[var, variable_b]
                    if not overlap:
                        continue
                    i, j = overlap
                    if word_a[i] != word_b[j]:
                        degree += 1
            degrees[word_a] = degree
        return sorted(self.domains[var], key=lambda x: degrees[x])

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        result_list = list(self.domains.keys() - assignment.keys())
        remaining_values = {key: len(self.domains[key]) for key in result_list}
        degrees = {key: len(self.crossword.neighbors(key)) for key in result_list}
        return sorted(result_list, key=lambda x: (remaining_values[x], -degrees[x]))[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        print("Hello world ass: ", assignment)

        if self.assignment_complete(assignment):
            return assignment
        
        unassigned_var = self.select_unassigned_variable(assignment)
        ordered = self.order_domain_values(unassigned_var, assignment)

        for value in ordered:
            updated_assignment = deepcopy(assignment)
            print("assignment = ", assignment)
            print("updated_assignment = ", updated_assignment)
            updated_assignment[unassigned_var] = value
            if self.consistent(updated_assignment):
                solution = self.backtrack(updated_assignment)
                if solution:
                    return solution
        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    print("words:", words)
    print("structure:", structure)

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)

    for y in range(crossword.height):
        outp = ""
        for x in range(crossword.width):
            structure = crossword.structure[y][x]
            outp += str(structure) + ", "
        print("row:", outp)

    for v in crossword.variables:
        i = v.i
        j = v.j
        direction = v.direction
        length = v.length
        cells = v.cells
        print("")
        print("Variable: i =", i, ", j = ", j, ", direction = ", direction, ", length = ", length)
        print("cells =", cells)
        print("")

    for v1 in crossword.variables:
        for v2 in crossword.variables:

            if v1 == v2:
                continue
            
            if crossword.overlaps[v1, v2]:
                print("V1: i =", v1)
                print("V2: i =", v2)
                olaps = crossword.overlaps[(v1, v2)]

                
                print("Olaps:", olaps)
                print("----")


    print("--------------------")
    print("--------------------")
    
    for x in crossword.variables:
        print("Variable: ", x)
        neighbors = crossword.neighbors(x)
        print("Neighbors: ", neighbors)
        print("")
    print("--------------------")
    print("--------------------")
    print("--------------------")
    print("--------------------")
    domain_keys = list(creator.domains.keys())
    for key in domain_keys:
        print("Domain ", key, " =", creator.domains[key])
        print("--------------------")
    print("--------------------")
    print("--------------------")
    print("--------------------")
    print("--------------------")

    print("done!")

    #_ = revise(0, 0)
    print("Hello")

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
