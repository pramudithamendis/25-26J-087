from scipy.optimize import linprog



# profit
# z = x1 + x2 - 50
    # Since this is a maximization problem and therefore let's continue without any changes
    #Take all to LHS
    # -x1 - x2 + 50 + z = 0

#machine A constraint
    # 50x1 + 24x2 ≤ 2400


#machine B constraint
    # 30x1 + 33x2 ≤ 2100
    
#Usual constraint
# x1, x2>= 0

obj = [-1, -1]

lhs_ineq = [[50, 24],  # Manpower
            [30, 33]]  # Material B

rhs_ineq = [ 2400,  # Manpower
            2100]  # Material B

bounds = []
for i in range(len(obj)):
    bounds.append((0, float("inf")))


opt = linprog(c=obj, A_ub=lhs_ineq, b_ub=rhs_ineq,bounds=bounds, method="highs")



print("Whether the optimum point could be found:\t", opt.success)
print("Maximum value:\t", opt.fun)
print("Best values for x1, x2:\t",opt.x)