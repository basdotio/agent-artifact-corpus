/**
 * Shared pagination footer — page size selector + prev/next navigation.
 * Used by AgentRegistry and RiskyAgents grids.
 */
import React from "react";
import { Text, Button, Dropdown, Option, makeStyles, type SelectionEvents, type OptionOnSelectData } from "@fluentui/react-components";
import { ChevronLeftRegular, ChevronRightRegular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  paginationContainer: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    height: "32px",
    paddingTop: "24px",
    borderTop: "1px solid #e0e0e0",
  },
  pageSizeSection: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  paginationLabel: {
    fontSize: "14px",
    color: "#242424",
  },
  dropdown: {
    minWidth: "80px",
    width: "80px",
    height: "32px",
  },
  navigationSection: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  navButton: {
    height: "32px",
    border: "0.8px solid rgba(0,0,0,0)",
    borderRadius: "4px",
  },
});

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
  pageSizes: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

export function Pagination({
  currentPage,
  totalPages,
  totalCount,
  pageSize,
  pageSizes,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  const styles = useStyles();

  return (
    <div className={styles.paginationContainer}>
      <div className={styles.pageSizeSection}>
        <Text className={styles.paginationLabel}>Show</Text>
        <Dropdown
          value={String(pageSize)}
          selectedOptions={[String(pageSize)]}
          onOptionSelect={(_: SelectionEvents, d: OptionOnSelectData) => {
            if (d.optionValue) {
              onPageSizeChange(parseInt(d.optionValue, 10));
            }
          }}
          className={styles.dropdown}
        >
          {pageSizes.map((s) => (
            <Option key={s} value={String(s)}>{String(s)}</Option>
          ))}
        </Dropdown>
        <Text className={styles.paginationLabel}>records per page</Text>
      </div>
      <div className={styles.navigationSection}>
        <Button
          icon={<ChevronLeftRegular />}
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 0}
          className={styles.navButton}
        >
          Previous
        </Button>
        <Text className={styles.paginationLabel}>
          Page {currentPage + 1} of {totalPages} ({totalCount} total)
        </Text>
        <Button
          icon={<ChevronRightRegular />}
          iconPosition="after"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages - 1}
          className={styles.navButton}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
