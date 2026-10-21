/**
 * Shared Assign Owner panel — people-picker UI for reassigning agent ownership.
 * Used by both AgentRegistry and AgentMap detail drawers.
 */
import React, { useState, useCallback } from "react";
import {
  Text,
  Button,
  Field,
  Avatar,
  Tag,
  TagPicker,
  TagPickerList,
  TagPickerInput,
  TagPickerControl,
  TagPickerOption,
  TagPickerGroup,
  tokens,
} from "@fluentui/react-components";
import { ChevronLeftRegular, DismissRegular } from "@fluentui/react-icons";

interface User {
  id: string;
  displayName: string;
  mail: string;
}

interface AssignOwnerPanelProps {
  users: User[];
  onAssign: (userId: string) => void;
  onBack: () => void;
  onClose: () => void;
  description?: string;
}

export function AssignOwnerPanel({
  users,
  onAssign,
  onBack,
  onClose,
  description = "Some organizations require agents to have owners for compliance purposes. The agent's owner can edit the agent, publish updates, delete it, or share it with teammates. You can select any user who has a license for Microsoft 365 Copilot.",
}: AssignOwnerPanelProps) {
  const [peopleSearch, setPeopleSearch] = useState("");
  const [peopleResults, setPeopleResults] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedUserName, setSelectedUserName] = useState("");

  const handleSearchPeople = useCallback(
    (query: string) => {
      if (!query.trim()) {
        setPeopleResults([]);
        return;
      }
      const q = query.toLowerCase();
      const filtered = users
        .filter(
          (u) =>
            u.displayName.toLowerCase().includes(q) ||
            u.mail?.toLowerCase().includes(q),
        )
        .slice(0, 10);
      setPeopleResults(filtered);
    },
    [users],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Top bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <Button appearance="subtle" size="small" icon={<ChevronLeftRegular />} onClick={onBack}>
          Back
        </Button>
        <Button appearance="subtle" size="small" icon={<DismissRegular />} onClick={onClose} />
      </div>

      {/* Title */}
      <Text size={600} weight="bold" style={{ display: "block", marginBottom: "12px" }}>
        Assign a new owner
      </Text>
      <Text size={300} style={{ color: tokens.colorNeutralForeground2, display: "block", marginBottom: "24px", lineHeight: "1.5" }}>
        {description}
      </Text>

      {/* TagPicker for user search */}
      <Field label="Search for a user" style={{ marginBottom: "16px" }}>
        <TagPicker
          onOptionSelect={(_, data) => {
            if (data.value === "no-options") return;
            setSelectedUserId(data.value);
            const user = peopleResults.find((u) => u.id === data.value);
            if (user) setSelectedUserName(user.displayName);
            setPeopleSearch("");
            setPeopleResults([]);
          }}
          selectedOptions={selectedUserId ? [selectedUserId] : []}
        >
          <TagPickerControl>
            <TagPickerGroup aria-label="Selected user">
              {selectedUserId && selectedUserName && (
                <Tag
                  key={selectedUserId}
                  shape="rounded"
                  media={<Avatar aria-hidden name={selectedUserName} color="colorful" />}
                  value={selectedUserId}
                >
                  {selectedUserName}
                </Tag>
              )}
            </TagPickerGroup>
            <TagPickerInput
              aria-label="Search by name or email"
              placeholder={selectedUserId ? "" : "Search by name or email address"}
              value={peopleSearch}
              onChange={(e) => {
                const v = e.target.value;
                setPeopleSearch(v);
                handleSearchPeople(v);
              }}
            />
          </TagPickerControl>
          <TagPickerList>
            {peopleResults.filter((u) => u.id !== selectedUserId).length === 0 && peopleSearch.trim() ? (
              <TagPickerOption value="no-options">No users found</TagPickerOption>
            ) : (
              peopleResults
                .filter((u) => u.id !== selectedUserId)
                .map((user) => (
                  <TagPickerOption
                    key={user.id}
                    value={user.id}
                    secondaryContent={user.mail}
                    media={<Avatar aria-hidden name={user.displayName} color="colorful" />}
                  >
                    {user.displayName}
                  </TagPickerOption>
                ))
            )}
          </TagPickerList>
        </TagPicker>
      </Field>

      {/* Assign button */}
      <div style={{ paddingTop: "16px", borderTop: `1px solid ${tokens.colorNeutralStroke1}` }}>
        <Button
          appearance="primary"
          disabled={!selectedUserId}
          onClick={() => {
            if (selectedUserId) onAssign(selectedUserId);
          }}
        >
          Assign
        </Button>
      </div>
    </div>
  );
}
