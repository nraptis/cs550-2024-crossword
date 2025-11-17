import sys
from crossword import *
from collections import deque
from copy import deepcopy
#from PIL import Image, ImageDraw, ImageFont

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

        for variable in self.crossword.variables:
            #we only keep the words that are the right length for the slot/variable.
            remove = set()
            for value in self.domains[variable]:
                if len(value) != variable.length:
                    remove.add(value)
            self.domains[variable] -= remove
            
    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        
        overlap = self.crossword.overlaps[x, y]
        if not overlap:
            return False
        
        revised = False
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
                revised = True
        self.domains[x] -= remove
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        
        if arcs is not None:
            queue = deque(arcs)
        else:
            queue = deque(
                (x, y)
                for x in self.crossword.variables
                for y in self.crossword.neighbors(x)
            )

        while queue:
            x, y = queue.pop()
            if self.revise(x, y):

                #return False if one or more domains end up empty.
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

        #There should be 1 assignment for every one of the crossword's variables.
        if len(assignment) != len(self.crossword.variables):
            return False
        
        #Every assignment variable must appear in the crossword's variables.
        #Every word in the assignment must be valid (sanity check).
        for variable in assignment:
            if variable not in self.crossword.variables:
                return False
            if assignment[variable] is None:
                return False
            
        return True
    
    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """

        #Cond 1.) All values are distinct.
        def contains_duplicates(elements):
            return len(elements) != len(set(elements))
        if contains_duplicates(assignment.values()):
            return False
        
        #Cond 2.) Every value is the correct length.
        for variable in assignment:
            if len(assignment[variable]) != variable.length:
                return False
            
        #Cond 3.) There are no conflicts between neighboring variables.
        for variable_a in assignment:
            for variable_b in self.crossword.neighbors(variable_a):
                if variable_b not in assignment:
                    continue

                word_a = assignment[variable_a]
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

        #MILK BONE
        variable_a = var

        #Any neighbor that already has a value assigned should be ignored.
        #LCV only considers how our choice affects *UNASSIGNED* neighbors.
        unassigned_neighbors = [
            neighbor
            for neighbor in self.crossword.neighbors(variable_a)
            if neighbor not in assignment
        ]

        rule_out_counts = {}

        #Loop through every possible word for the chosen variable.
        for word_a in self.domains[variable_a]:
            rule_out_count = 0

            #For each unassigned neighbor, check how many of its words violate constraint.
            for variable_b in unassigned_neighbors:
                overlap = self.crossword.overlaps[variable_a, variable_b]
                if not overlap:
                    continue
                i, j = overlap

                #Count how many of neighbor's words disagree at the overlapping letter.
                for word_b in self.domains[variable_b]:
                    if word_a[i] != word_b[j]:
                        rule_out_count += 1
            
            #Store how many neighbor values this choice would eliminate.
            rule_out_counts[word_a] = rule_out_count

        #Return values sorted so the LEAST constraining word comes first.
        sort_key = lambda variable: rule_out_counts[variable]
        return sorted(self.domains[variable_a], key=sort_key)

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        # Collect all variables that do NOT yet appear in the assignment.
        # These are the only variables we are allowed to choose next.
        unassigned = list(self.crossword.variables - assignment.keys())

        # MRV heuristic:
        remaining_values = {variable: len(self.domains[variable]) for variable in unassigned}

        # Degree heuristic:
        degrees = {variable: len(self.crossword.neighbors(variable)) for variable in unassigned}

        # Select the variable with:
        #   1.) The fewest remaining values (MRV heuristic)
        #   2.) If tied, the most neighbors (Degree heuristic)
        sort_key = lambda variable: (
            remaining_values[variable],
            -degrees[variable]
        )

        #return sorted(unassigned, key=sort_key)[0]
        return min(unassigned, key=sort_key)
    
    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        
        # If the assignment is complete, we've succeeded.
        if self.assignment_complete(assignment):
            return assignment
        
        # Smartly select a variable to assign using MRV + Degree heuristic.
        var = self.select_unassigned_variable(assignment)

        # Try values in least-constraining order
        for value in self.order_domain_values(var, assignment):
            
            # Tentatively assign the value.
            assignment[var] = value

            # If this partial assignment is still consistent, recurse...
            if self.consistent(assignment):
                solution = self.backtrack(assignment)
                if solution:
                    return solution
            
            # This didn't work, backtrack and unassign the value.
            del assignment[var]

        # No solution was found, harakiri.
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
