# Farm Finance Platform Frontend

This is the frontend application for the Farm Finance Platform, featuring a climate data visualization dashboard.

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
# or
yarn install
```

2. Start the development server:
```bash
npm start
# or
yarn start
```

3. Open [http://localhost:3000](http://localhost:3000) to view the application in your browser.

## Features

### Climate Data Dashboard

The Climate Data Dashboard is a comprehensive visualization tool for monitoring climate conditions affecting farmers:

- **Climate Statistics**: View aggregated NDVI and rainfall anomaly statistics
- **Interactive Map**: Visualize farmer locations with color-coded climate risk indicators
- **Risk Assessment**: Track climate risk distribution across your farmer base
- **Detailed Farmer View**: Access detailed climate data for individual farmers
- **Historical Data**: View charts of climate data history for each farmer
- **Tabular View**: Browse all climate data in a sortable table format

### Key Components

- **NDVI Visualization**: The Normalized Difference Vegetation Index ranges from -0.1 (barren) to 0.9 (lush vegetation) and is visualized using a color gradient from brown to green.
- **Rainfall Anomaly**: Deviation from historical rainfall averages in millimeters, visualized from brown (drought) to blue (excess).
- **Risk Assessment**: Combines NDVI and rainfall anomaly data to categorize climate risk as Low, Medium, or High.

## API Integration

The dashboard integrates with the following backend API endpoints:

- `/api/farmers/climate_data/`: Retrieves climate data for all farmers
- `/api/farmers/climate_stats/`: Fetches aggregated climate statistics
- `/api/farmers/{id}/climate_history/`: Gets historical climate data for a specific farmer

## Dependencies

- **React**: Frontend library for building user interfaces
- **React Router**: For application routing
- **React Bootstrap**: UI component library
- **Chart.js / React-Chartjs-2**: For data visualization charts
- **Leaflet / React-Leaflet**: For interactive maps
- **Axios**: For API requests

## Development

### Project Structure

```
src/
├── App.js             # Main application component with routing
├── App.css            # Global styles
├── components/        # Application components
│   ├── ClimateDataDashboard.js   # Climate dashboard component
│   └── [other components]
└── [other files]
```

### Extending the Dashboard

To extend the dashboard with new visualizations:

1. Add new API endpoints in the backend
2. Create new chart components in the dashboard
3. Add new metrics to the risk calculation logic

## License

This project is licensed under the MIT License - see the LICENSE file for details. 