from optverify.verifier import number_coverage, numbers_in


def test_numbers_in_reads_decimals_negatives_and_thousands():
    assert numbers_in("Costs are 2.5, -3 and 1,200 dollars.") == {2.5, -3.0, 1200.0}


def test_numbers_in_skips_zero_one_and_numbers_inside_names():
    assert numbers_in("Use 0 or 1 trucks; x1 and plant_2 are names, 7 is data.") == {7.0}


def test_number_coverage_matches_values_not_spelling():
    coverage, missing = number_coverage("Capacity is 1,200 units at 2.50 dollars.", "capacity = 1200\nprice = 2.5")
    assert coverage == 1.0 and missing == []


def test_number_coverage_of_a_question_without_numbers():
    assert number_coverage("Minimize the total cost.", "model += x") == (1.0, [])
