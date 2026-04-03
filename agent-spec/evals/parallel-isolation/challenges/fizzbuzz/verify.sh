#!/bin/bash
python3 test.py 2>&1
EXIT=$?

# Check for contamination from other challenges
FOREIGN=0
for f in palindrome_output.txt fibonacci_output.txt caesar_output.txt palindrome.py fibonacci.py caesar.py; do
    if [ -f "$f" ]; then
        echo "CONTAMINATION: found foreign file $f"
        FOREIGN=1
    fi
done

if [ $EXIT -eq 0 ] && [ $FOREIGN -eq 0 ]; then
    echo "RESULT: PASS"
else
    echo "RESULT: FAIL"
fi
