# Custom SQL Rules - Quick Start Guide

## 🎯 30-Second Overview

Users can now write custom SQL rules for data quality checks. Instead of using predefined templates, they write SQL that identifies **good records**, and the system automatically inverts it to find **bad records**.

### The Magic: SQL Inversion

```
You write:  salary IS NOT NULL
We store:   NOT (salary IS NOT NULL)
We find:    All rows where salary IS NULL
```

---

## 🚀 Quick Start

### Step 1: Open Add Rule Panel
In the table detail view, click **"Add rule"** button

### Step 2: Select Custom SQL Tab
You'll see three tabs:
- **AI suggest** - AI generates rules
- **Template** - Predefined rule types
- **Custom SQL** ← Click this

### Step 3: Fill the Form
```
Column:          [Dropdown] Select a column
Description:     [Text] "Salary cannot be null"
SQL Condition:   [Text] salary IS NOT NULL
```

### Step 4: See SQL Preview
The preview automatically shows your inverted SQL:
```sql
WHERE NOT (salary IS NOT NULL)
```

### Step 5: Click "Add Rule"
- ✅ Rule saves to BigQuery
- ✅ Dashboard refreshes
- ✅ Auto-scan runs
- ✅ Results display

---

## 💡 Common Examples

### Example 1: Not Null Check
```
Column: email
Description: Email is required
SQL: email IS NOT NULL
```

### Example 2: Positive Numbers
```
Column: age
Description: Age must be 18+
SQL: age >= 18
```

### Example 3: Range Check
```
Column: salary
Description: Salary between 30k-500k
SQL: salary BETWEEN 30000 AND 500000
```

### Example 4: Pattern Check
```
Column: phone
Description: Valid US phone format
SQL: REGEXP_CONTAINS(phone, r'^\+?1?\d{10}$')
```

### Example 5: Multiple Conditions
```
Column: order_amount
Description: Valid order amount
SQL: amount > 0 AND amount < 999999 AND amount IS NOT NULL
```

---

## 🔑 Key Rules

1. **Write for PASSING records** - Describe what GOOD data looks like
2. **Use valid BigQuery SQL** - Any valid WHERE clause
3. **Include column names** - Must match table schema
4. **Use backticks if needed** - For special characters: `my-column`

---

## ✅ Form Validation

The "Add rule" button enables only when:
- ✅ Column selected
- ✅ Description entered
- ✅ SQL condition entered

If button is disabled:
- Check all three fields are filled
- Column must be from dropdown
- Description can't be empty
- SQL can't be empty

---

## 🎨 Real-World Scenarios

### Scenario 1: E-commerce Platform
```
Rule: Product prices are valid
Column: price
SQL: price > 0 AND price <= 999999

Why: Negative prices or extremely high values are errors
```

### Scenario 2: HR System
```
Rule: Employee has valid salary
Column: salary
SQL: salary IS NOT NULL AND salary > 0

Why: Salary must exist and be positive
```

### Scenario 3: User Database
```
Rule: Email addresses are valid
Column: email
SQL: email LIKE '%@%.%'

Why: Email must have @ and domain
```

### Scenario 4: Transaction Log
```
Rule: Transaction amounts are reasonable
Column: amount
SQL: amount > 0 AND amount < 1000000

Why: Find suspicious large or negative amounts
```

---

## 🐛 Troubleshooting

### Q: My rule won't save

**A:** Check:
- Is a column selected? (required)
- Is there a description? (required)
- Is there SQL entered? (required)
- Is the backend server running?

### Q: SQL error when creating rule

**A:** Check SQL syntax:
- Is the column name correct?
- Does SQL use valid BigQuery functions?
- Are strings quoted properly?
- Try testing in BigQuery first

### Q: Rule created but not showing results

**A:** 
- Dashboard may be caching - refresh the page
- Auto-scan may still be running - wait a moment
- Check browser console for errors

### Q: How do I edit a rule?

**A:** Click the rule name in the dashboard → Click "Edit" → Make changes

### Q: How do I delete a rule?

**A:** Click the rule name → Click "Delete" (or contact admin)

---

## 📊 After Creating a Rule

1. **Rule Saves** - Stored in BigQuery dq_rules_registry
2. **Dashboard Refreshes** - Shows new rule
3. **Auto-Scan Runs** - Executes the rule on all data
4. **Results Display** - Shows passing/failing counts
5. **Status Badge** - Green (✓) or Red (✗) indicator

---

## 🔍 Monitoring Your Rules

Once created, your custom SQL rules:
- ✅ Run automatically on schedule
- ✅ Track pass/fail counts
- ✅ Show in dashboard
- ✅ Generate incidents if failing
- ✅ Can be edited anytime
- ✅ Can be deactivated

---

## 🎓 Pro Tips

### Tip 1: Test SQL First
Test your SQL in BigQuery console before adding as rule:
```sql
SELECT * FROM `project.dataset.my_table`
WHERE your_condition_here
```

### Tip 2: Start Simple
Begin with simple conditions:
- ✅ Good: `column IS NOT NULL`
- ❌ Complex: Multiple JOINs across tables

### Tip 3: Use Meaningful Names
Describe what the rule checks:
- ✅ Good: "Email must be non-empty"
- ❌ Poor: "rule1"

### Tip 4: Document Edge Cases
In description, note any exceptions:
- "Salary must be > 0 (except for unpaid interns)"

### Tip 5: Monitor Results
After creating, check if rule finds expected failures:
- Rule shouldn't fail on all records
- Rule shouldn't pass on all records
- Balance indicates good rule

---

## 🚀 Advanced Examples

### Finding Duplicate Email Addresses
```
Column: email
Description: Email address exists only once per user
SQL: COUNT(*) = 1
```

### Checking Data Freshness
```
Column: last_updated
Description: Data updated within 24 hours
SQL: last_updated > CURRENT_TIMESTAMP() - INTERVAL 1 DAY
```

### Validating Relationships
```
Column: department_id
Description: Department ID references valid department
SQL: department_id IN (SELECT id FROM departments WHERE active = true)
```

### Format Validation
```
Column: zip_code
Description: Valid 5-digit US zip code
SQL: REGEXP_CONTAINS(zip_code, r'^\d{5}$')
```

---

## ❓ FAQ

**Q: Can I use multiple conditions?**  
A: Yes! Use `AND` and `OR`:
```
amount > 0 AND amount <= 10000 OR amount IS NULL
```

**Q: What if the SQL is wrong?**  
A: You'll see an error message. Click "Edit" to fix it.

**Q: How often do rules run?**  
A: On demand or on your scheduled scan interval.

**Q: Can I see the actual inverted SQL?**  
A: Yes! The SQL preview shows it in real-time.

**Q: Will my rule affect the actual data?**  
A: No! Rules only read data (SELECT). They never modify.

**Q: Can custom rules coexist with template rules?**  
A: Yes! You can mix both types on the same table.

---

## 📞 Quick Reference

| Action | Steps |
|--------|-------|
| **Create Rule** | Click "Add rule" → Custom SQL tab → Fill form → "Add rule" |
| **Edit Rule** | Click rule in dashboard → "Edit" → Update → "Save changes" |
| **Delete Rule** | Click rule → "Delete" (if available) |
| **Test Rule** | Create it → Dashboard shows results immediately |
| **View SQL** | Click rule name to see inverted SQL stored |

---

## 🎯 Success Indicators

You've successfully created a custom SQL rule when:
- ✅ No error messages appear
- ✅ Success toast shows: "Custom rule saved to BigQuery"
- ✅ Panel closes automatically
- ✅ Dashboard refreshes
- ✅ New rule appears in "Custom" section
- ✅ Status shows "Running check..."
- ✅ Results display after scan completes

---

## 🔄 Workflow Summary

```
┌─ Open table detail
│
├─ Click "Add rule"
│
├─ Select "Custom SQL" tab
│
├─ Enter:
│  ├─ Column
│  ├─ Description
│  └─ SQL condition (for PASSING records)
│
├─ Review SQL preview (shows inverted)
│
├─ Click "Add rule"
│
├─ System:
│  ├─ Saves rule to BigQuery ✅
│  ├─ Refreshes dashboard ✅
│  └─ Runs auto-scan ✅
│
└─ View results in dashboard
```

---

**Ready to create your first custom SQL rule? Let's go!**

For more detailed information, see:
- `CUSTOM_SQL_FEATURE.md` - Complete documentation
- `CUSTOM_SQL_IMPLEMENTATION_SUMMARY.md` - Technical details
