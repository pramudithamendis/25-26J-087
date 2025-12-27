from scipy.optimize import linprog



# profit
# -z = -8x1  -10x2 -7x3
    # Since this is a minimization problem, let's make it to Maximization problem
    # z = 8x1  10x2 + 7x3
    # Now, take all to LHS
    # -8x1 - 10x2 - 7x3 + z = 0

#(wood?) constraint
    # x1 + 3x2 + 2x3 ≤ 10


#(wood?) constraint
    # −x1 − 5x2 − x3 ≥ −8  
    # Since >= is there, let's turn to <=
    # 𝑥1 + 5𝑥2 + 𝑥3 ≤ 8

#Usual constraint
# x1, x2, x3>= 0

obj = [-8, -10, -7]

lhs_ineq = [[1, 3, 2],  # Manpower
            [1, 5, 1]]  # Material B

rhs_ineq = [ 10,  # Manpower
            8]  # Material B

bounds = []
for i in range(len(obj)):
    bounds.append((0, float("inf")))


opt = linprog(c=obj, A_ub=lhs_ineq, b_ub=rhs_ineq,bounds=bounds, method="highs")



print("Whether the optimum point could be found:\t", opt.success)
print("Minimum cost:\t", opt.fun)
print("Best values for x1, x2, x3:\t",opt.x)