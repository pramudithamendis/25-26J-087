from scipy.optimize import linprog



# profit
# z = 5x1 + 10x2
    # Since this is a maximization problem and therefore let's continue without any changes
    #Take all to LHS
    # -5x1 - 10x2 + z = 0

#banana constraint
    # 8.8x1 + 5.2x2 >= 20
    # since >= is there, let's turn to <=
    # -8.8x1 - 5.2x2 <= -20


#apple constraint
    # 8.8x1 + 5.2x2 ≤ 60
    
#Usual constraint
# x1, x2>= 0

obj = [-5, -10]

lhs_ineq = [[-8.8, -5.2],  
            [8.8, 5.2]]  

rhs_ineq = [ 20,  
            60]  

bounds = []
for i in range(len(obj)):
    bounds.append((0, float("inf")))


opt = linprog(c=obj, A_ub=lhs_ineq, b_ub=rhs_ineq,bounds=bounds, method="highs")



print("Whether the optimum point could be found:\t", opt.success)
print("Minimum cost:\t", opt.fun)
print("Best values for x1, x2:\t",opt.x)