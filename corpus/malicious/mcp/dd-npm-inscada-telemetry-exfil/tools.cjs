/**
 * inSCADA Tool Definitions
 * Claude API tool_use formatında tool tanımları
 * inSCADA REST API + Chart
 */

const TOOLS = [
  // ==================== Space Management ====================
  {
    name: "set_space",
    description: "Switch the active space. Updates the X-Space header sent with all API requests. Use this before accessing data in a different space.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {
        space_name: { type: "string", description: "Space name (e.g. default_space, production, test)" },
      },
      required: ["space_name"],
    },
  },
  // ==================== inSCADA Data Tools ====================
  {
    name: "list_spaces",
    description: "List all inSCADA spaces. Spaces are the top level of the hierarchy.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        search: { type: "string", description: "Search in space name (optional)" },
      },
    },
  },
  {
    name: "list_projects",
    description: "List projects under a space. Returns project ID, name, description, and location.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        space_id: { type: "number", description: "Space ID" },
        space_name: { type: "string", description: "Space name (partial match)" },
        search: { type: "string", description: "Search in project name (optional)" },
      },
    },
  },
  {
    name: "list_variables",
    description: "List all SCADA variables (tags/points) in a project. Returns ALL variables — use search_variables instead when you need to filter by name or description.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID" },
        connection_id: { type: "number", description: "Filter by connection ID (optional)" },
        page_size: { type: "number", description: "Results per page (default: 500, max: 2000)" },
        page_number: { type: "number", description: "Page number (default: 0)" },
        verbose: { type: "boolean", description: "Return all fields (default: false — compact: name, type, unit, dsc, id)" },
      },
      required: ["project_id"],
    },
  },
  {
    name: "search_variables",
    description: "Search SCADA variables by name, description, type, connection, device, or frame. Uses server-side filtering — much faster and lighter than listing all variables. Use this when user asks to find or filter variables.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID" },
        name: { type: "string", description: "Search in variable name (contains match)" },
        dsc: { type: "string", description: "Search in variable description (contains match)" },
        type: { type: "string", description: "Variable type filter (e.g. Float, Integer, Boolean, String)" },
        connection_id: { type: "number", description: "Filter by connection ID" },
        device_id: { type: "number", description: "Filter by device ID" },
        frame_id: { type: "number", description: "Filter by frame ID" },
        page_size: { type: "number", description: "Results per page (default: 50, max: 500)" },
        page_number: { type: "number", description: "Page number (default: 0)" },
        verbose: { type: "boolean", description: "Return all fields (default: false — compact: name, type, unit, dsc, id)" },
      },
      required: ["project_id"],
    },
  },
  {
    name: "list_scripts",
    description: "List scripts in a project. Returns script ID, name, description, schedule type. Code content is not included.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID" },
        project_name: { type: "string", description: "Project name (partial match)" },
        space_name: { type: "string", description: "Filter by space name" },
        search: { type: "string", description: "Search in script name" },
      },
    },
  },
  {
    name: "get_script",
    description: "Get full script code and details. Returns code, schedule config, owner, and history.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        script_id: { type: "number", description: "Script ID" },
        script_name: { type: "string", description: "Script name (partial match)" },
        project_name: { type: "string", description: "Filter by project name" },
      },
    },
  },
  {
    name: "update_script",
    description: `Update script code. Read with get_script first. Call inscada_guide for full script rules and ins.* API reference.

CRITICAL RULES (always apply):
- Nashorn ECMAScript 5 ONLY. DO NOT USE: let, const, =>, template literals, destructuring, async/await, class.
- STRUCTURE: function main() { /* code */ } main();
- Historical date: dttm is ISO string, NOT epoch. new Date(isoString) returns NaN in Nashorn. Use: ("" + items[i].dttm).substring(11, 19)
- Logged data is reverse-ordered (newest first) → use reverse loop for charts.`,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        script_id: { type: "number", description: "Script ID (required)" },
        code: { type: "string", description: "New script code (full code). Nashorn ES5: function main(){...} main(); structure required." },
      },
      required: ["script_id", "code"],
    },
  },
  {
    name: "list_connections",
    description: "List connections in a project. With include_status=true, also returns connection status (Connected/Disconnected).",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID (optional, lists all connections if omitted)" },
        search: { type: "string", description: "Search in connection name (optional)" },
        include_status: { type: "boolean", description: "Include connection status (Connected/Disconnected)" },
      },
    },
  },
  {
    name: "search_in_scripts",
    description: "Search for text within all script code. Returns matching scripts with line numbers.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        search_text: { type: "string", description: "Text to search for" },
        project_name: { type: "string", description: "Filter by project name" },
      },
      required: ["search_text"],
    },
  },
  // ==================== Animation Tools ====================
  {
    name: "list_animations",
    description: "List animations in a project. Lightweight — SVG content not included.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID" },
        project_name: { type: "string", description: "Project name (used if project_id not provided)" },
        search: { type: "string", description: "Search in animation name (optional)" },
      },
    },
  },
  {
    name: "get_animation",
    description: "Get animation details, elements, and linked scripts.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        animation_id: { type: "number", description: "Animation ID" },
        animation_name: { type: "string", description: "Animation name (partial match, used if animation_id not provided)" },
        project_id: { type: "number", description: "Project ID (for name-based search)" },
        include_svg: { type: "boolean", description: "Include SVG content (default: false)" },
        include_elements: { type: "boolean", description: "Include elements (default: true)" },
      },
    },
  },
  // ==================== inSCADA REST API Tools ====================
  {
    name: "inscada_get_live_value",
    description: "Read the LIVE (real-time, current) value of a single SCADA variable. MUST use this tool when user asks for current/live/real-time value. Returns value, timestamp, and variable info. project_id is optional (auto-detected if omitted).",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID (optional, auto-detected if omitted)" },
        variable_name: { type: "string", description: "Variable name" },
        verbose: { type: "boolean", description: "Return full API response with all fields (default: false — returns compact response)" },
      },
      required: ["variable_name"],
    },
  },
  {
    name: "inscada_get_live_values",
    description: "Read LIVE (real-time, current) values of multiple SCADA variables in one call. MUST use this for batch live value queries. Returns {varName: {value, date}} map. project_id is optional (auto-detected if omitted).",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID (optional, auto-detected if omitted)" },
        variable_names: { type: "string", description: "Comma-separated variable names" },
        verbose: { type: "boolean", description: "Return full API response (default: false — compact)" },
      },
      required: ["variable_names"],
    },
  },
  {
    name: "inscada_set_value",
    description: "Write a value to a SCADA variable. WARNING: Sends commands to real equipment.",
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID" },
        variable_name: { type: "string", description: "Variable name" },
        value: { type: "number", description: "Value to write" },
      },
      required: ["project_id", "variable_name", "value"],
    },
  },
  {
    name: "inscada_get_fired_alarms",
    description: "List active (fired) alarms. Returns alarm name, status, trigger time, description.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID (optional, lists all alarms if omitted)" },
      },
    },
  },
  {
    name: "inscada_connection_status",
    description: "Check connection status (Connected/Disconnected) for given connection IDs.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        connection_ids: { type: "string", description: "Comma-separated connection IDs" },
      },
      required: ["connection_ids"],
    },
  },
  {
    name: "inscada_project_status",
    description: "Check project runtime status: scripts, connections, alarm groups, data transfers, reports.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID" },
      },
      required: ["project_id"],
    },
  },
  {
    name: "inscada_run_script",
    description: "Execute a script on the inSCADA server. Returns the script's return value.",
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        script_id: { type: "number", description: "Script ID" },
      },
      required: ["script_id"],
    },
  },
  {
    name: "inscada_script_status",
    description: "Check script execution status (Not Scheduled, Running, etc.).",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        script_id: { type: "number", description: "Script ID" },
      },
      required: ["script_id"],
    },
  },
  {
    name: "inscada_logged_values",
    description: "Fetch historical logged data for variables (time series). Returns [{value, dttm, name, projectId}].",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        variable_ids: { type: "string", description: "Comma-separated variable IDs" },
        start_date: { type: "string", description: "Start date (ISO 8601 or yyyy-MM-dd HH:mm:ss)" },
        end_date: { type: "string", description: "End date (ISO 8601 or yyyy-MM-dd HH:mm:ss)" },
      },
      required: ["variable_ids"],
    },
  },
  {
    name: "inscada_logged_stats",
    description: "Get variable statistics (min, max, avg, sum, count, first, last) over a time range. Supports hourly or daily grouping.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        project_id: { type: "number", description: "Project ID" },
        variable_names: { type: "string", description: "Comma-separated variable names" },
        time_range: { type: "string", description: "Time range (1h, 24h, 7d)" },
        start_date: { type: "string", description: "Start date (ISO 8601, optional)" },
        end_date: { type: "string", description: "End date (ISO 8601, optional)" },
        interval: { type: "string", enum: ["daily", "hourly"], description: "Grouping interval (default: daily)" },
      },
      required: ["project_id", "variable_names"],
    },
  },

  // ==================== Chart Tools ====================
  {
    name: "chart_line",
    description: "Generate a time-series line chart. Fetches historical data from REST API automatically.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {
        variable_names: { type: "string", description: "Comma-separated variable names" },
        project_id: { type: "number", description: "Project ID" },
        time_range: { type: "string", description: "Time range (1h, 6h, 24h, 7d)" },
        start_date: { type: "string", description: "Start date (optional, alternative to time_range)" },
        end_date: { type: "string", description: "End date (optional)" },
        title: { type: "string" },
        y_label: { type: "string", description: "Y-axis unit label" },
      },
      required: ["variable_names", "project_id"],
    },
  },
  {
    name: "chart_bar",
    description: "Generate a bar chart for variable comparison (statistics). Supports mean, max, min, sum, count aggregation.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {
        variable_names: { type: "string", description: "Comma-separated variable names" },
        project_id: { type: "number", description: "Project ID" },
        aggregation: { type: "string", description: "mean, max, min, sum, count (default: mean)" },
        time_range: { type: "string", description: "Time range (1h, 24h, 7d)" },
        start_date: { type: "string", description: "Start date (optional)" },
        end_date: { type: "string", description: "End date (optional)" },
        title: { type: "string" },
        y_label: { type: "string" },
      },
      required: ["variable_names", "project_id"],
    },
  },
  {
    name: "chart_gauge",
    description: "Display a live gauge indicator. With auto_refresh=true (default), updates every 2 seconds from REST API. Use this for real-time gauge display instead of inscada_get_live_value.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {
        variable_name: { type: "string", description: "Variable name (single)" },
        project_id: { type: "number", description: "Project ID" },
        min: { type: "number", description: "Min value (default: 0)" },
        max: { type: "number", description: "Max value (default: 100)" },
        title: { type: "string" },
        unit: { type: "string", description: "Unit label" },
        auto_refresh: { type: "boolean", description: "Live update on/off (default: true)" },
      },
      required: ["variable_name", "project_id"],
    },
  },
  {
    name: "chart_multi",
    description: "Plot multiple data series on the same chart. Useful for comparing different variables.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {
        series: {
          type: "array",
          description: "Series: [{variable_name, project_id, label}]",
          items: {
            type: "object",
            properties: {
              variable_name: { type: "string", description: "Variable name" },
              project_id: { type: "number", description: "Project ID" },
              label: { type: "string", description: "Series label" },
            },
            required: ["variable_name", "project_id"],
          },
        },
        time_range: { type: "string", description: "Time range (1h, 6h, 24h, 7d)" },
        start_date: { type: "string", description: "Start date (optional)" },
        end_date: { type: "string", description: "End date (optional)" },
        title: { type: "string" },
        y_label: { type: "string" },
      },
      required: ["series"],
    },
  },
  {
    name: "chart_forecast",
    description: "Generate historical + forecast chart. Historical as solid line, forecast as dashed line. Analyze data first, then generate forecast_values.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {
        variable_names: { type: "string", description: "Comma-separated variable names" },
        project_id: { type: "number", description: "Project ID" },
        time_range: { type: "string", description: "Historical data range (6h, 24h, 7d)" },
        start_date: { type: "string", description: "Start date (optional)" },
        end_date: { type: "string", description: "End date (optional)" },
        forecast_values: {
          type: "array",
          description: "Tahmin noktaları [{x: ISO_timestamp, y: number}]",
          items: {
            type: "object",
            properties: {
              x: { type: "string", description: "ISO timestamp" },
              y: { type: "number", description: "Value" },
            },
            required: ["x", "y"],
          },
        },
        forecast_label: { type: "string", description: "Forecast label (default: Forecast)" },
        title: { type: "string" },
        y_label: { type: "string", description: "Y-axis unit label" },
      },
      required: ["variable_names", "project_id", "forecast_values"],
    },
  },

  // ==================== Custom Menu Tools (REST API) ====================
  {
    name: "list_custom_menus",
    description: "List custom menus (3-level hierarchy). Returns menu ID, name, icon, position.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        search: { type: "string", description: "Search in menu name (optional)" },
      },
    },
  },
  {
    name: "get_custom_menu",
    description: "Get custom menu details and HTML content by ID.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        custom_menu_id: { type: "number", description: "Custom Menu ID" },
      },
      required: ["custom_menu_id"],
    },
  },
  {
    name: "get_custom_menu_by_name",
    description: "Find and get custom menu details by name (exact match).",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Menu name (exact match)" },
      },
      required: ["name"],
    },
  },
  {
    name: "create_custom_menu",
    description: "Create a custom menu page. USE TEMPLATES (gauge/line_chart/gauge_and_chart/multi_chart) when possible — no content needed with templates.",
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        name: { type: "string", description: "Menu name" },
        content: { type: "string", description: "HTML/JS/CSS content (only when NOT using template)" },
        icon: { type: "string", description: "Font Awesome 5.x class (default: fas fa-industry)" },
        target: { type: "string", description: "Target location (default: Home)" },
        position: { type: "string", enum: ["Top", "Bottom"], description: "Position (default: Bottom)" },
        menu_order: { type: "number", description: "Sort order (default: 1)" },
        parent_menu_id: { type: "number", description: "Parent menu ID (for 2nd level)" },
        second_menu_id: { type: "number", description: "2nd level ID (for 3rd level)" },
        template: { type: "string", enum: ["gauge", "line_chart", "gauge_and_chart", "multi_chart"], description: "Template type" },
        variable_name: { type: "string", description: "Template variable name" },
        project_id: { type: "number", description: "Template project ID" },
        title: { type: "string", description: "Dashboard title" },
        unit: { type: "string", description: "Unit (kW, °C, bar, %)" },
        min: { type: "number", description: "Gauge min (default: 0)" },
        max: { type: "number", description: "Gauge max (default: 100)" },
        refresh_interval: { type: "number", description: "Refresh interval ms (default: 2000)" },
        time_range: { type: "string", description: "Time window (default: 1h)" },
        space_name: { type: "string", description: "Space name (default: default_space)" },
        variables: {
          type: "array",
          description: "multi_chart template için değişken listesi",
          items: {
            type: "object",
            properties: {
              name: { type: "string", description: "Variable name" },
              label: { type: "string", description: "Display label (optional, defaults to name)" },
              color: { type: "string", description: "Line color (optional, e.g. #3b82f6)" },
            },
            required: ["name"],
          },
        },
      },
      required: ["name"],
    },
  },
  {
    name: "update_custom_menu",
    description: "Update an existing custom menu. Read with get_custom_menu first. Can use templates to regenerate content.",
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        custom_menu_id: { type: "number", description: "Custom Menu ID" },
        name: { type: "string", description: "Menu name" },
        content: { type: "string", description: "HTML content (when not using template)" },
        icon: { type: "string", description: "Font Awesome icon class" },
        target: { type: "string", description: "Target location" },
        position: { type: "string", description: "Position" },
        menu_order: { type: "number", description: "Sort order" },
        parent_menu_id: { type: "number", description: "Parent menu ID" },
        second_menu_id: { type: "number", description: "2nd level ID" },
        template: { type: "string", enum: ["gauge", "line_chart", "gauge_and_chart", "multi_chart"], description: "Template type" },
        variable_name: { type: "string", description: "Variable name" },
        project_id: { type: "number", description: "Project ID" },
        title: { type: "string", description: "Title" },
        unit: { type: "string", description: "Unit" },
        min: { type: "number", description: "Gauge min" },
        max: { type: "number", description: "Gauge max" },
        refresh_interval: { type: "number", description: "Refresh interval ms" },
        time_range: { type: "string", description: "Time window" },
        space_name: { type: "string", description: "Space name" },
        variables: {
          type: "array",
          description: "multi_chart template için değişken listesi",
          items: {
            type: "object",
            properties: {
              name: { type: "string", description: "Variable name" },
              label: { type: "string", description: "Display label" },
              color: { type: "string", description: "Line color" },
            },
            required: ["name"],
          },
        },
      },
      required: ["custom_menu_id"],
    },
  },
  {
    name: "delete_custom_menu",
    description: "Delete a custom menu by ID.",
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        custom_menu_id: { type: "number", description: "Custom Menu ID" },
        parent_menu_id: { type: "number", description: "Parent menu ID" },
        second_menu_id: { type: "number", description: "2nd level ID" },
      },
      required: ["custom_menu_id"],
    },
  },

  // ==================== Export Tools ====================
  {
    name: "export_excel",
    description: "Export data to Excel (.xlsx) file. Supports multiple sheets. Returns a download link.",
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {
        file_name: { type: "string", description: "File name (without .xlsx extension)" },
        sheets: {
          type: "array",
          description: "Excel sheets. Each contains {name, headers, rows}.",
          items: {
            type: "object",
            properties: {
              name: { type: "string", description: "Sheet name (max 31 chars)" },
              headers: { type: "array", items: { type: "string" }, description: "Column headers" },
              rows: { type: "array", items: { type: "array" }, description: "Row data (2D array)" },
            },
            required: ["name", "headers", "rows"],
          },
        },
      },
      required: ["file_name", "sheets"],
    },
  },
  // ==================== Generic API Tools ====================
  {
    name: "inscada_api_endpoints",
    description: "Discover inSCADA REST API endpoints. Search/filter among 625 endpoints by keyword, category, or HTTP method.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        search: { type: "string", description: "Search term (searches in path, summary, tag). E.g. 'alarm group', 'trend', 'report'" },
        category: { type: "string", description: "Category filter: alarms, variables, connections, scripts, projects, reports, visualization, trends, users, spaces, menus, expressions, data-transfer, custom, protocols, templates, system, other" },
        method: { type: "string", enum: ["GET", "POST", "PUT", "DELETE", "PATCH"], description: "HTTP method filter" },
        tag: { type: "string", description: "OpenAPI tag filter (controller name). E.g. 'alarm-group', 'trend-controller'" },
        limit: { type: "number", description: "Max results (default: 30, max: 50)" },
      },
    },
  },
  {
    name: "inscada_api_schema",
    description: "Get parameter and body schema for an API endpoint. Use before calling inscada_api to know required parameters.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: "Endpoint path (e.g. /api/alarms/groups)" },
        method: { type: "string", description: "HTTP method (default: GET)" },
      },
      required: ["path"],
    },
  },
  {
    name: "inscada_api",
    description: `Send generic HTTP request to inSCADA REST API. Access any /api/ endpoint. Non-GET requests require user confirmation. Use dedicated tools (inscada_get_live_value, list_variables, etc.) when available — only use this for endpoints without a dedicated tool. Call inscada_guide for animation creation rules, element types, and SVG requirements.

Key rules:
- Frame variables: 2-step. (1) POST /api/variables/filter/pages body:{projectId,frameId} → var list, (2) inscada_get_live_values → values.
- SVG REQUIRED: <svg> must include style="width:100%;height:100%;" viewBox="0 0 1920 1080" width="1920" height="1080".
- Animation props must never be null (at least "{}"). SVG ids = domId.`,
    annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true },
    input_schema: {
      type: "object",
      properties: {
        method: { type: "string", enum: ["GET", "POST", "PUT", "DELETE", "PATCH"], description: "HTTP method (default: GET)" },
        path: { type: "string", description: "API path (must start with /api/). Path params use {id} format. E.g. /api/projects/{id}/status" },
        query_params: { type: "object", description: "Query string parameters. E.g. {projectId: 52, groupName: 'test'}. Array values are exploded." },
        body: { type: "object", description: "Request body (for POST/PUT/PATCH). JSON object." },
        path_params: { type: "object", description: "Path parameters. E.g. {id: 52} → /api/projects/52/status" },
      },
      required: ["path"],
    },
  },
  {
    name: "inscada_guide",
    description: "IMPORTANT: Call this tool FIRST before using any other inSCADA tool in a new conversation. Returns comprehensive usage guide including: Nashorn script rules (ECMAScript 5), ins.* API reference (30+ methods), animation element types (27 types), chart rules, custom menu rules, live value endpoints, tool priorities, and best practices. Without this guide you will make errors.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "inscada_animation_guide",
    description: "Returns detailed animation element rules: expression return types, dynamic props via return objects, SVG structure requirements, and element-specific examples. Call this BEFORE creating or modifying animations. The main inscada_guide gives a summary — this tool gives the full animation reference.",
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    input_schema: {
      type: "object",
      properties: {},
    },
  },
];

module.exports = TOOLS;
