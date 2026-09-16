# Default Code Review Categories

This reference file contains common categories that typically emerge from PR review comments. These serve as a guide for the analysis process but are not prescriptive - the actual categories should be derived from the specific comments in your repository.

## Common Categories

### Code Organization & Architecture
- Component structure and hierarchy
- Module boundaries and separation of concerns
- File and folder organization
- Dependency management
- Code reusability and DRY principles

### Naming Conventions
- Variable and function naming patterns
- Component and class naming
- File naming conventions
- Consistency in terminology
- Meaningful and descriptive names

### Error Handling
- Try-catch patterns
- Error propagation strategies
- User-facing error messages
- Logging and debugging information
- Graceful degradation

### Testing & Test Coverage
- Unit test patterns
- Integration test approaches
- Test organization and structure
- Edge case coverage
- Mock and stub usage
- Test data management

### Performance & Optimization
- Unnecessary re-renders (React)
- Memoization strategies
- Database query optimization
- Bundle size considerations
- Lazy loading patterns
- Caching strategies

### Security
- Input validation and sanitization
- Authentication and authorization patterns
- Secure data handling
- API security
- Dependency vulnerabilities

### Code Style & Formatting
- Indentation and whitespace
- Line length and wrapping
- Import organization
- Comment style and placement
- Consistent code formatting

### Documentation
- Code comments and explanations
- Function and component documentation
- README and setup instructions
- API documentation
- Inline documentation for complex logic

### Type Safety
- TypeScript usage and patterns
- Type definitions and interfaces
- Generic type usage
- Type narrowing and guards
- Any type avoidance

### React/Component Patterns (if applicable)
- Component composition
- Prop drilling and context usage
- Custom hooks patterns
- Side effect management (useEffect)
- State management strategies
- Component lifecycle

### API Design
- REST endpoint design
- Request/response structures
- API versioning
- Error response formats
- Pagination patterns

### Database & Queries
- Query optimization
- Index usage
- Transaction patterns
- Schema design
- Data migration strategies

### State Management
- Redux/Zustand/other state library patterns
- Global vs local state decisions
- State normalization
- Async state handling
- State update patterns

### Accessibility
- ARIA labels and roles
- Keyboard navigation
- Screen reader compatibility
- Focus management
- Color contrast and visibility

### DevOps & Deployment
- CI/CD pipeline patterns
- Environment configuration
- Build optimization
- Deployment strategies
- Monitoring and logging

## Category Selection Guidelines

When analyzing PR comments, Claude should:

1. **Identify natural groupings** - Look for themes that emerge from the comments themselves
2. **Avoid over-categorization** - Combine related concepts rather than creating too many narrow categories
3. **Use clear names** - Category names should be immediately understandable
4. **Prioritize actionability** - Focus on categories that lead to concrete, actionable guidelines
5. **Adapt to context** - Different projects may need different categories based on their tech stack and domain

## Example Category Structure

```
best-practices/
├── README.md                          # Index of all categories
├── code-organization.md               # Architecture and structure
├── naming-conventions.md              # Naming patterns
├── error-handling.md                  # Error handling patterns
├── testing.md                         # Testing best practices
├── performance.md                     # Performance optimization
├── security.md                        # Security practices
├── react-patterns.md                  # React-specific patterns (if applicable)
├── type-safety.md                     # TypeScript patterns (if applicable)
└── ...                                # Additional categories as needed
```
