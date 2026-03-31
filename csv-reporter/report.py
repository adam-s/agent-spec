import csv
from collections import defaultdict

with open("data/sales.csv") as f:
    rows = list(csv.DictReader(f))

# 1. Total Revenue
total_revenue = sum(float(r["revenue"]) for r in rows)
print(f"Total Revenue: ${total_revenue:.2f}")

# 2. Top 3 Products by Units Sold
units_by_product = defaultdict(int)
for r in rows:
    units_by_product[r["product"]] += int(r["units"])
top3 = sorted(units_by_product.items(), key=lambda x: x[1], reverse=True)[:3]
print("Top 3 Products by Units Sold:", ", ".join(f"{p} ({u})" for p, u in top3))

# 3. Revenue by Region (descending)
revenue_by_region = defaultdict(float)
for r in rows:
    revenue_by_region[r["region"]] += float(r["revenue"])
sorted_regions = sorted(revenue_by_region.items(), key=lambda x: x[1], reverse=True)
print("Revenue by Region:", ", ".join(f"{reg} (${rev:.2f})" for reg, rev in sorted_regions))

# 4. Highest Revenue Month
revenue_by_month = defaultdict(float)
for r in rows:
    month = r["date"][:7]
    revenue_by_month[month] += float(r["revenue"])
best_month = max(revenue_by_month.items(), key=lambda x: x[1])
print(f"Highest Revenue Month: {best_month[0]} (${best_month[1]:.2f})")

# 5. Highest Average Order Value by Product
revenue_by_product = defaultdict(float)
orders_by_product = defaultdict(int)
for r in rows:
    revenue_by_product[r["product"]] += float(r["revenue"])
    orders_by_product[r["product"]] += 1
avg_order = {p: revenue_by_product[p] / orders_by_product[p] for p in revenue_by_product}
best_product = max(avg_order.items(), key=lambda x: x[1])
print(f"Highest Avg Order Value: {best_product[0]} (${best_product[1]:.2f})")
