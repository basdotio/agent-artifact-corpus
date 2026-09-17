---
name: r-parabola-plotter
description: Create parabola plots using R with customizable coefficients, range, styling, and annotations. Use for mathematical visualization, quadratic function analysis, and educational demonstrations of parabolic curves.
---

## Overview

This skill generates professional parabola plots using R's ggplot2 library. It handles quadratic functions of the form y = ax² + bx + c with full customization options including vertex marking, axis of symmetry, and roots.

## When to Use This Skill

Use this skill when the user asks to:
- Plot a parabola or quadratic function
- Visualize y = ax² + bx + c
- Graph polynomial functions (degree 2)
- Show quadratic relationships
- Create mathematical visualizations with parabolas
- Demonstrate vertex, roots, or axis of symmetry

## Required Information

To create a parabola plot, you need:
- **Coefficient a** (default: 1) - Controls width and direction
- **Coefficient b** (default: 0) - Controls horizontal position
- **Coefficient c** (default: 0) - Controls vertical position
- **X range** (default: -10 to 10) - Domain to plot

## R Code Template

Always use this template structure:

```r
# Install and load required packages
if (!require("ggplot2")) install.packages("ggplot2")
library(ggplot2)

# Define parabola coefficients
a <- 1    # Change this value
b <- 0    # Change this value
c <- 0    # Change this value

# Define x range
x_min <- -10
x_max <- 10

# Create data
x <- seq(x_min, x_max, length.out = 500)
y <- a * x^2 + b * x + c

# Create data frame
df <- data.frame(x = x, y = y)

# Calculate vertex
vertex_x <- -b / (2 * a)
vertex_y <- a * vertex_x^2 + b * vertex_x + c

# Calculate roots (if they exist)
discriminant <- b^2 - 4*a*c
has_real_roots <- discriminant >= 0

if (has_real_roots) {
  root1 <- (-b + sqrt(discriminant)) / (2*a)
  root2 <- (-b - sqrt(discriminant)) / (2*a)
}

# Create the plot
p <- ggplot(df, aes(x = x, y = y)) +
  geom_line(color = "blue", size = 1.2) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray50") +
  geom_vline(xintercept = 0, linetype = "dashed", color = "gray50") +
  geom_point(aes(x = vertex_x, y = vertex_y), 
             color = "red", size = 3, shape = 19) +
  geom_vline(xintercept = vertex_x, linetype = "dotted", 
             color = "red", alpha = 0.5) +
  annotate("text", x = vertex_x, y = vertex_y, 
           label = sprintf("Vertex (%.2f, %.2f)", vertex_x, vertex_y),
           hjust = -0.1, vjust = 1.5, color = "red", size = 4) +
  labs(
    title = sprintf("Parabola: y = %.2fx² + %.2fx + %.2f", a, b, c),
    subtitle = sprintf("Vertex: (%.2f, %.2f)", vertex_x, vertex_y),
    x = "x", 
    y = "y"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    plot.title = element_text(face = "bold", hjust = 0.5),
    plot.subtitle = element_text(hjust = 0.5),
    panel.grid.minor = element_blank()
  )

# Add roots if they exist
if (has_real_roots) {
  p <- p + 
    geom_point(aes(x = root1, y = 0), 
               color = "green", size = 3, shape = 17) +
    geom_point(aes(x = root2, y = 0), 
               color = "green", size = 3, shape = 17) +
    annotate("text", x = root1, y = 0, 
             label = sprintf("Root (%.2f, 0)", root1),
             hjust = 0.5, vjust = -1, color = "green", size = 3.5) +
    annotate("text", x = root2, y = 0, 
             label = sprintf("Root (%.2f, 0)", root2),
             hjust = 0.5, vjust = -1, color = "green", size = 3.5)
  
  p <- p + labs(
    subtitle = sprintf("Vertex: (%.2f, %.2f) | Roots: %.2f, %.2f", 
                      vertex_x, vertex_y, root1, root2)
  )
} else {
  p <- p + labs(
    subtitle = sprintf("Vertex: (%.2f, %.2f) | No real roots", 
                      vertex_x, vertex_y)
  )
}

# Display the plot
print(p)

# Save the plot
ggsave("parabola_plot.png", plot = p, width = 10, height = 7, dpi = 300)
cat("\nPlot saved as 'parabola_plot.png'\n")
```

## Customization Options

### Basic Parabolas
- **Standard parabola**: a=1, b=0, c=0 → y = x²
- **Inverted parabola**: a=-1, b=0, c=0 → y = -x²
- **Wider parabola**: a=0.5, b=0, c=0 → y = 0.5x²
- **Narrower parabola**: a=2, b=0, c=0 → y = 2x²

### Shifted Parabolas
- **Vertical shift**: Keep a=1, b=0, change c
- **Horizontal shift**: Keep a=1, c=0, change b
- **Both shifts**: Modify b and c together

### X Range Adjustment
```r
# For wide parabolas, use larger range
x_min <- -20
x_max <- 20

# For narrow parabolas, use smaller range
x_min <- -5
x_max <- 5

# Asymmetric ranges are fine too
x_min <- -15
x_max <- 5
```

### Color Schemes
```r
# Change the main curve color
geom_line(color = "darkblue", size = 1.5)

# Change vertex color
geom_point(..., color = "darkred", size = 4)

# Change roots color
geom_point(..., color = "darkgreen", size = 4)
```

## Instructions for Response

When creating a parabola plot:

1. **Ask for coefficients** if not provided:
   - "What values would you like for a, b, and c?"
   - Or suggest defaults: "I'll use a=1, b=0, c=0 for a standard parabola"

2. **Modify the template**:
   - Replace the a, b, c values
   - Adjust x_min and x_max if needed
   - Keep all the vertex and root calculations

3. **Provide the complete R code**:
   - Include all necessary libraries
   - Use the full template (don't abbreviate)
   - Ensure code is ready to run as-is

4. **Explain the plot features**:
   - Where the vertex is located
   - Whether roots exist and where
   - The direction (opens up/down)
   - Any special characteristics

5. **Suggest variations**:
   - "Want to see it with different coefficients?"
   - "Would you like to compare multiple parabolas?"
   - "Should I adjust the x-range to show more detail?"

## Example Responses

### Example 1: Simple Request
**User**: "Plot a parabola"

**Response**: "I'll create a standard parabola plot (y = x²) for you using R. Here's the code:"

```r
[Include full code with a=1, b=0, c=0]
```

"This creates a parabola that:
- Opens upward (a > 0)
- Has its vertex at the origin (0, 0)
- Is symmetric about the y-axis
- Passes through the origin (which is both the vertex and a root)"

### Example 2: Specific Function
**User**: "Plot y = 2x² - 4x + 1"

**Response**: "I'll plot the parabola y = 2x² - 4x + 1. Here's the R code:"

```r
[Include full code with a=2, b=-4, c=1]
```

"This parabola:
- Opens upward (a = 2 > 0)
- Has vertex at (1, -1)
- Has axis of symmetry at x = 1
- Has two real roots at approximately x = 0.29 and x = 1.71"

### Example 3: Educational Context
**User**: "Show me how changing 'a' affects the parabola"

**Response**: "Great question! Let me create code that plots multiple parabolas with different 'a' values to demonstrate the effect:"

```r
[Provide code that overlays multiple parabolas]
```

## Common Variations

### Multiple Parabolas on One Plot
```r
# Create data for multiple parabolas
df_multi <- data.frame()
a_values <- c(0.5, 1, 2, -1)

for (a in a_values) {
  x <- seq(-5, 5, length.out = 200)
  y <- a * x^2
  temp_df <- data.frame(x = x, y = y, 
                        a = as.factor(sprintf("a = %.1f", a)))
  df_multi <- rbind(df_multi, temp_df)
}

ggplot(df_multi, aes(x = x, y = y, color = a)) +
  geom_line(size = 1.2) +
  theme_minimal() +
  labs(title = "Effect of coefficient 'a' on parabola shape",
       color = "Coefficient")
```

### Interactive Plot (using plotly)
```r
library(plotly)

plot_ly(df, x = ~x, y = ~y, type = 'scatter', mode = 'lines',
        name = sprintf('y = %.2fx² + %.2fx + %.2f', a, b, c)) %>%
  layout(title = "Interactive Parabola Plot",
         xaxis = list(title = "x", zeroline = TRUE),
         yaxis = list(title = "y", zeroline = TRUE))
```

## Error Handling

If the user provides invalid input:
- **Non-numeric coefficients**: Ask for numbers
- **a = 0**: Explain this isn't a parabola (it's linear)
- **Extreme values**: Suggest adjusting x-range or y-range

## Quality Checklist

Before providing the final code, ensure:
- [ ] Coefficients a, b, c are clearly defined
- [ ] X range is appropriate for the parabola width
- [ ] Vertex calculation is included
- [ ] Root calculation handles the discriminant
- [ ] Plot includes proper labels and title
- [ ] Vertex is marked and labeled
- [ ] Roots are marked if they exist
- [ ] Code is complete and runnable
- [ ] Plot will be saved to a file