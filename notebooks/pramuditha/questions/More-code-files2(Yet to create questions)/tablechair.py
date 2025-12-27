import streamlit as st
from scipy.optimize import linprog

# x = table
# y = chair
st.subheader("Let's calculate the best count of table and chairs to produce to maximize profit.")
board_feet = int(st.text_input("Boardfeet available", 300))
man_hours = int(st.text_input("labour hours available", 110))

profit_table = int(st.text_input("Profit from a table", 6))
profit_chair = int(st.text_input("Profit from a chair", 8))



# profit
# z = 6x1 + 8x2
    # Since this is a maximization problem and therefore let's continue without any changes
    # -6x1 - 8x2 + z = 0

#wood constraint
    # 30x1 + 20x2 ≤ 300


#labour constraint
    # 5x1 + 10x2 ≤ 110
    
#Usual constraint
# x1, x2>= 0
profit_table = -1 * profit_table
profit_chair = -1 * profit_chair
obj = [profit_table, profit_chair]

lhs_ineq = [[30, 20],  # Manpower
            [5, 10]]  # Material B

rhs_ineq = [ board_feet,  # Manpower
            man_hours]  # Material B

bounds = []
for i in range(len(obj)):
    bounds.append((0, float("inf")))


opt = linprog(c=obj, A_ub=lhs_ineq, b_ub=rhs_ineq,bounds=bounds, method="highs")

print()
print()
print("Whether the optimum point could be found:\t", opt.success)
print("Minimum cost:\t", opt.fun)
print("Best values for x1, x2, x3:\t",opt.x)
print("The result is proved with the snap in  'C:\MY FILES\SLIIT\Y3S1\IT3071\Snaps\ 24 9 23'")
print()
print()
st.write("To calculate the best count of table and chairs to produce to maximize profit, click \"Generate\"")
if st.button("Generate"):
    text = "To maximize profit, make "+ str(round(opt.x[0]))+ " tables, and make "+ str(round(opt.x[1]))+ " chairs"
    st.success(text)
