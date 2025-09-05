# Project Refactor and Feature Enhancements

## 1. Line Graph Issue  
- Currently, the line graph is rendering as blank and not displaying the data correctly.  
- Please fix this so that the data is properly fetched, processed, and visualized.  

## 2. Filtering Functionality  
- Articles should be filterable by **sentiment** and **source**.  
- Users should also have the option to display **all articles** at once without filters.  

## 3. Frontend & Backend Architecture  
- Switch the **frontend to JavaScript**, enabling easier integration with charts, filters, and interactive UI elements.  
- The backend should be powered by **Flask**, exposing APIs that the frontend can call for article data, sentiment values, and historical trends.  
- Refactor `server.py` and update how it integrates with `HistoricalDataGetter`, so the backend delivers data in a structured, consumable format for the frontend.  

## 4. Scalability & Flexibility  
- If you believe there’s a better architectural approach than Flask + JS for scaling future features, propose and implement it.  
- The system should be flexible enough to expand with more filters, chart types, and data streams in the future.  

## 5. Theme Support  
- Currently, the **text colors for the pie charts do not change** when switching themes (e.g., light/dark mode).  
- Update the chart rendering logic so that text, labels, and axis colors adapt dynamically to the active theme as they are currently stuck as dark grey.  

## 6. Testing with Playwright MCP  
- Use **Playwright MCP tests** to confirm that all visual elements (charts, filters, themes, etc.) are rendering correctly.  
- Ensure automated tests catch issues such as blank graphs, incorrect theme application, or broken filters.  

## 7. Filesystem organization
- You may organize the current file system if you deem it to be unsustainable for future updates.

## 8. Fix article count
- Currently, the articles are showing the results in "recent_articles" instead of "raw_articles" meaning that only 5 out of the potentially 20+ articles are showing at once.

## Goal  
A working system where:  
- The line graph displays correctly.  
- Articles can be filtered (by sentiment and source, or all).  
- The frontend is interactive (JavaScript) and communicates seamlessly with the backend (Flask or a better alternative).  
- Theme changes update chart colors properly.  
- Visual rendering is validated through Playwright MCP tests.  

