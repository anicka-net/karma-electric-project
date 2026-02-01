#!/bin/bash
# Check progress on 110 practice response generation

echo "============================================================"
echo "Practice Response Generation - Progress Check"
echo "============================================================"
echo ""

BASE="/home/anicka/karma-electric/data/practice-responses"

echo "Category Progress:"
echo ""

# Creative-Artistic (need 20)
CREATIVE=$(find "$BASE/creative-artistic" -name "*-response.json" 2>/dev/null | wc -l)
echo "✓ Creative-Artistic:        $CREATIVE/20"

# Disability-Accessibility (need 15)
DISABILITY=$(find "$BASE/disability-accessibility" -name "*-response.json" 2>/dev/null | wc -l)
if [ "$DISABILITY" -eq 15 ]; then
    echo "✓ Disability-Accessibility: $DISABILITY/15"
else
    echo "  Disability-Accessibility: $DISABILITY/15"
fi

# Financial-Life-Admin (need 20)
FINANCIAL=$(find "$BASE/financial-life-admin" -name "*-response.json" 2>/dev/null | wc -l)
if [ "$FINANCIAL" -eq 20 ]; then
    echo "✓ Financial-Life-Admin:     $FINANCIAL/20"
else
    echo "  Financial-Life-Admin:     $FINANCIAL/20"
fi

# Technical-Kindness (need 60 total, currently have 35, need 25 more)
TECHNICAL=$(find "$BASE/technical-kindness" -name "*-response.json" 2>/dev/null | wc -l)
if [ "$TECHNICAL" -ge 60 ]; then
    echo "✓ Technical-Kindness:       $TECHNICAL/60"
else
    echo "  Technical-Kindness:       $TECHNICAL/60 (need 25 more: 036-060)"
fi

# Parenting (need 45 total, currently have 20, need 25 more)
PARENTING=$(find "$BASE/parenting" -name "*-response.json" 2>/dev/null | wc -l)
if [ "$PARENTING" -ge 45 ]; then
    echo "✓ Parenting:                $PARENTING/45"
else
    echo "  Parenting:                $PARENTING/45 (need 25 more: 021-045)"
fi

echo ""
echo "------------------------------------------------------------"

TOTAL=$((CREATIVE + DISABILITY + FINANCIAL))
# For tech and parenting, only count the new ones needed
TECH_NEW=$((TECHNICAL > 35 ? TECHNICAL - 35 : 0))
PARENT_NEW=$((PARENTING > 20 ? PARENTING - 20 : 0))
TOTAL_NEW=$((TOTAL + TECH_NEW + PARENT_NEW))

echo "Total Progress: $TOTAL_NEW/110 new responses"
echo ""

REMAINING=$((110 - TOTAL_NEW))
if [ "$REMAINING" -eq 0 ]; then
    echo "🎉 All 110 responses complete!"
    echo ""
    echo "Next steps:"
    echo "1. python3 scripts/check_practice_leakage.py"
    echo "2. Review sample responses for quality"
    echo "3. Update progress docs"
else
    echo "Remaining: $REMAINING responses"
    echo ""
    echo "Next category to complete:"
    if [ "$DISABILITY" -lt 15 ]; then
        echo "  → Disability-Accessibility: $((15 - DISABILITY)) remaining"
    elif [ "$FINANCIAL" -lt 20 ]; then
        echo "  → Financial-Life-Admin: $((20 - FINANCIAL)) remaining"
    elif [ "$TECHNICAL" -lt 60 ]; then
        echo "  → Technical-Kindness: $((60 - TECHNICAL)) remaining (036-060)"
    elif [ "$PARENTING" -lt 45 ]; then
        echo "  → Parenting: $((45 - PARENTING)) remaining (021-045)"
    fi
fi

echo ""
echo "============================================================"
