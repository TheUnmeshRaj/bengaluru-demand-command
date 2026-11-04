
import csv

file_path = "rides_contextual_synthetic.csv"

previous_timestamp = None
out_of_order_count = 0
first_examples = []

with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row_number, row in enumerate(reader, start=2):
        current_timestamp = row["Timestamp"].strip()

        if (
            previous_timestamp is not None
            and current_timestamp < previous_timestamp
        ):
            out_of_order_count += 1

            if len(first_examples) < 5:
                first_examples.append(
                    (row_number, previous_timestamp, current_timestamp)
                )

        previous_timestamp = current_timestamp

print("Timestamp order check")
print("---------------------")
print("Out-of-order records:", out_of_order_count)

if out_of_order_count == 0:
    print("Dataset is chronologically sorted.")
else:
    print("Dataset needs chronological sorting.")
    print("\nFirst few violations:")

    for example in first_examples:
        print(example)
