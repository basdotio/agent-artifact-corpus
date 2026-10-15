# MultiEdit Tool Behavior Documentation

This document contains exhaustive tests of the MultiEdit tool to discover its precise behavior in all edge cases.

## ✅ Experiment: Basic successful single edit
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "happy"}])
```
Applied 1 edit to /Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt:
1. Replaced "jolly" with "happy"
```

## ✅ Experiment: Multiple edits where one has duplicate matches
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "happy"}, {"old_string": "swagman", "new_string": "traveler"}, {"old_string": "billabong", "new_string": "waterhole"}])
```
<error>Found 2 matches of the string to replace, but replace_all is false. To replace all occurrences, set replace_all to true. To replace only one occurrence, please provide more context to uniquely identify the instance.
String: swagman</error>
```
Note: When any edit in the array fails validation, the entire operation fails. The error message helpfully suggests using replace_all for multiple matches.

## ✅ Experiment: Multiple successful edits with replace_all
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "happy"}, {"old_string": "swagman", "new_string": "traveler", "replace_all": true}, {"old_string": "billabong", "new_string": "waterhole", "replace_all": true}])
```
Applied 3 edits to /Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt:
1. Replaced "jolly" with "happy"
2. Replaced "swagman" with "traveler"
3. Replaced "billabong" with "waterhole"
```

## ✅ Experiment: Identical old_string and new_string
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "jolly"}])
```
<error>No changes to make: old_string and new_string are exactly the same.</error>
```
Note: The tool explicitly checks for and rejects no-op edits where old_string equals new_string.

## ✅ Experiment: Empty old_string
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "", "new_string": "hello"}])
```
<error>Cannot create new file - file already exists.</error>
```
Note: Empty old_string is interpreted as a file creation operation. This would succeed if the file didn't already exist.

## ✅ Experiment: Empty new_string (deletion)
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": ""}])
```
Applied 1 edit to /Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt:
1. Replaced "jolly" with ""
```
Note: Empty new_string successfully deletes the matched text. This is a useful feature for removing content.

## ✅ Experiment: Both old_string and new_string empty
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "", "new_string": ""}])
```
<error>No changes to make: old_string and new_string are exactly the same.</error>
```

## ✅ Experiment: Newline as old_string (without replace_all)
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "\n", "new_string": " "}])
```
<error>Found 32 matches of the string to replace, but replace_all is false. To replace all occurrences, set replace_all to true. To replace only one occurrence, please provide more context to uniquely identify the instance.
String: 
</error>
```
Note: The tool correctly identifies newline characters and counts all instances (32 newlines in the file). The error message shows the literal newline character.

## ✅ Experiment: Newline as old_string (with replace_all)
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "\n", "new_string": " ", "replace_all": true}])
```
Applied 1 edit to /Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt:
1. Replaced "
" with " "
```
Note: With replace_all=true, all newlines were successfully replaced with spaces, effectively converting the multi-line file to a single line.

## ✅ Experiment: Multiline old_string
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "once\na jolly\nswagman", "new_string": "once upon a time\na happy\ntraveler"}])
```
Applied 1 edit to /Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt:
1. Replaced "once
a jolly
swagman" with "once upon a time
a happy
traveler"
```
Note: MultiEdit successfully handles multiline strings. The output shows literal newlines in the replacement confirmation.

## ✅ Experiment: Empty edits array
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[])
```
<error>InputValidationError: [
  {
    "code": "too_small",
    "minimum": 1,
    "type": "array",
    "inclusive": true,
    "exact": false,
    "message": "At least one edit is required",
    "path": [
      "edits"
    ]
  }
]</error>
```
Note: The tool uses schema validation to require at least one edit in the array. This prevents empty operations.

## ✅ Experiment: Atomicity - mix of valid and invalid edits
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "happy"}, {"old_string": "DOESNOTEXIST", "new_string": "xyz"}, {"old_string": "swagman", "new_string": "traveler", "replace_all": true}])
```
<error>String to replace not found in file.
String: DOESNOTEXIST</error>
```
Note: Verified that the file remained unchanged - edits are atomic (all-or-nothing).

## ✅ Experiment: Sequential failure - first edit fails
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "DOESNOTEXIST", "new_string": "xyz"}, {"old_string": "jolly", "new_string": "happy"}, {"old_string": "swagman", "new_string": "traveler", "replace_all": true}])
```
<error>String to replace not found in file.
String: DOESNOTEXIST</error>
```
Note: When the first edit fails, subsequent edits are not attempted.

## ✅ Experiment: Overlapping edits - edit #1 output would be edit #2 input
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "jolly jolly"}, {"old_string": "jolly jolly", "new_string": "very happy"}])
```
<error>String to replace not found in file.
String: jolly jolly</error>
```

## ✅ Experiment: Overlapping edits - edit #1 creates text for edit #2
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "happy"}, {"old_string": "happy", "new_string": "very happy"}])
```
<error>String to replace not found in file.
String: happy</error>
```
Note: All edits are validated against the original file content before any are applied. Edits do NOT see the results of previous edits.

## ✅ Experiment: Successful sequential edits on different parts
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "once", "new_string": "Once"}, {"old_string": "a jolly", "new_string": "a happy"}, {"old_string": "swagman", "new_string": "traveler", "replace_all": true}])
```
Applied 3 edits to /Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt:
1. Replaced "once" with "Once"
2. Replaced "a jolly" with "a happy"
3. Replaced "swagman" with "traveler"
```

## ✅ Experiment: Conflicting/overlapping text regions
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "a jolly\nswagman", "new_string": "a happy\ntraveler"}, {"old_string": "jolly\nswagman\ncamped", "new_string": "merry\nvagabond\nrested"}])
```
<error>String not found in file. Failed to apply edit.</error>
```

## ✅ Experiment: replace_all parameter - explicit false
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "billabong", "new_string": "waterhole", "replace_all": false}])
```
<error>Found 2 matches of the string to replace, but replace_all is false. To replace all occurrences, set replace_all to true. To replace only one occurrence, please provide more context to uniquely identify the instance.
String: billabong</error>
```

## ✅ Experiment: replace_all parameter - omitted (default)
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "billabong", "new_string": "waterhole"}])
```
<error>Found 2 matches of the string to replace, but replace_all is false. To replace all occurrences, set replace_all to true. To replace only one occurrence, please provide more context to uniquely identify the instance.
String: billabong</error>
```

## ✅ Experiment: replace_all parameter - true
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "billabong", "new_string": "waterhole", "replace_all": true}])
```
Applied 1 edit to /Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt:
1. Replaced "billabong" with "waterhole"
```

## ✅ Experiment: Non-existent old_string - single edit
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "DEFINITELY_NOT_IN_FILE", "new_string": "something else"}])
```
<error>String to replace not found in file.
String: DEFINITELY_NOT_IN_FILE</error>
```

## ✅ Experiment: Duplicate edits - same edit twice
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "jolly", "new_string": "happy"}, {"old_string": "jolly", "new_string": "happy"}])
```
<error>String not found in file. Failed to apply edit.</error>
```
Note: This fails because edits are applied sequentially. After the first edit replaces "jolly" with "happy", the second edit can't find "jolly" anymore.

## ✅ Experiment: Second edit old_string identical to first edit new_string
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "till", "new_string": "the", "replace_all": true}, {"old_string": "the", "new_string": "some", "replace_all": true}])
```
<error>Cannot edit file: old_string is a substring of a new_string from a previous edit.</error>
```
Note: MultiEdit has protection against edits that would interfere with each other. When the old_string of a later edit exactly matches (or is a substring of) the new_string of an earlier edit, it blocks the operation to prevent unexpected behavior.

## ✅ Experiment: Second edit old_string is substring of first edit new_string  
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": "till", "new_string": "the"}, {"old_string": "he", "new_string": "we", "replace_all": true}])
```
<error>Cannot edit file: old_string is a substring of a new_string from a previous edit.</error>
```
Note: This confirms the protection mechanism also applies to substring relationships, not just exact matches. The tool detects that "he" is a substring of "the" and prevents the operation.

## ✅ Experiment: First edit creates concatenation, second edit operates on result
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=[{"old_string": " waited ", "new_string": ""}, {"old_string": "andtill", "new_string": "foobar"}])
```
<error>String to replace not found in file.
String: andtill</error>
```
Note: This experiment demonstrates that edits are validated against the original file content, not the result of previous edits. Even though removing " waited " from "and waited till" would create "andtill", the second edit fails because "andtill" doesn't exist in the original file.

## ✅ Experiment: Invalid edits parameter type
MultiEdit(file_path="/Users/ljw/code/mini_agent/test/sample_data/edit_root/file1.txt", edits=42)
```
<error>InputValidationError: MultiEdit failed due to the following issue:
The parameter `edits` type is expected as `array` but provided as `number`</error>
```
Note: The tool has proper type validation and provides clear error messages when the wrong parameter types are provided.

## Summary of Findings

Based on the exhaustive testing, here are the key behaviors of the MultiEdit tool:

1. **Basic Operation**: MultiEdit applies multiple find-and-replace operations to a single file in sequence.

2. **Atomicity**: Edits are atomic - if any edit fails, none are applied. The file remains unchanged.

3. **Sequential Application**: Edits are applied one after another, each operating on the result of the previous edit.

4. **Validation**: All edits are validated against the original file content before any are applied. If validation fails for any edit, the entire operation fails.

5. **Edge Cases**:
   - Empty old_string: Interpreted as creating a new file (fails if file exists)
   - Empty new_string: Deletes the matched text
   - Identical old_string and new_string: Rejected with error
   - Both empty: Rejected as identical strings
   - Empty edits array: Rejected with validation error

6. **String Matching**:
   - Supports newline characters and multiline replacements
   - Exact string matching required
   - Multiple occurrences require replace_all parameter

7. **replace_all Parameter**:
   - Defaults to false when omitted
   - When false and multiple matches exist, operation fails with helpful error
   - When true, replaces all occurrences

8. **Error Messages**: Clear and specific error messages indicate the exact problem and often suggest solutions.

