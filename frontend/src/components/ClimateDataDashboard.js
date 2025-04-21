import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Container, Row, Col, Card, Table, Badge, Spinner,
  ProgressBar
} from 'react-bootstrap';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

// Register chart components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

// Define API endpoints
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';
const CLIMATE_DATA_URL = `${API_BASE_URL}/api/farmers/climate_data/`;
const CLIMATE_STATS_URL = `${API_BASE_URL}/api/farmers/climate_stats/`;

// Risk level badge colors
const RISK_COLORS = {
  LOW: 'success',
  MEDIUM: 'warning',
  HIGH: 'danger',
  UNKNOWN: 'secondary'
};

const ClimateDataDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [climateData, setClimateData] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedFarmer, setSelectedFarmer] = useState(null);

  // Fetch climate data on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch climate data for all farmers
        const dataResponse = await axios.get(CLIMATE_DATA_URL);
        setClimateData(dataResponse.data);
        
        // Fetch aggregated statistics
        const statsResponse = await axios.get(CLIMATE_STATS_URL);
        setStats(statsResponse.data.data);
        
        setLoading(false);
      } catch (err) {
        setError('Error loading climate data. Please try again later.');
        setLoading(false);
        console.error('Error fetching climate data:', err);
      }
    };
    
    fetchData();
  }, []);

  // Fetch farmer climate history when a farmer is selected
  useEffect(() => {
    const fetchFarmerHistory = async () => {
      if (!selectedFarmer) return;
      
      try {
        const historyResponse = await axios.get(`${API_BASE_URL}/api/farmers/${selectedFarmer.id}/climate_history/`);
        setSelectedFarmer({
          ...selectedFarmer,
          history: historyResponse.data.data
        });
      } catch (err) {
        console.error('Error fetching farmer climate history:', err);
      }
    };
    
    if (selectedFarmer && !selectedFarmer.history) {
      fetchFarmerHistory();
    }
  }, [selectedFarmer]);

  // Function to calculate NDVI color (greener = healthier vegetation)
  const getNdviColor = (ndvi) => {
    if (ndvi === null || ndvi === undefined) return '#999999';
    
    // NDVI ranges from -0.1 (brown) to 0.9 (green)
    const normalizedValue = (ndvi + 0.1) / 1.0;
    const hue = normalizedValue * 120; // 0 = red, 120 = green
    return `hsl(${hue}, 80%, 40%)`;
  };

  // Function to get rainfall anomaly color
  const getRainfallColor = (anomaly) => {
    if (anomaly === null || anomaly === undefined) return '#999999';
    
    // Red for negative (drought), blue for positive (excess rain)
    if (anomaly < 0) {
      // Brown for drought (-30mm or worse = dark brown)
      const intensity = Math.min(1, Math.abs(anomaly) / 30);
      return `rgba(165, 42, 42, ${intensity})`;
    } else {
      // Blue for excess rain (30mm or more = dark blue)
      const intensity = Math.min(1, anomaly / 30);
      return `rgba(0, 0, 255, ${intensity})`;
    }
  };

  // Prepare chart data for selected farmer
  const getHistoryChartData = () => {
    if (!selectedFarmer || !selectedFarmer.history) return null;
    
    const labels = selectedFarmer.history.map(item => item.date).reverse();
    
    return {
      labels,
      datasets: [
        {
          label: 'NDVI Value',
          data: selectedFarmer.history.map(item => item.ndvi).reverse(),
          borderColor: 'rgb(75, 192, 75)',
          backgroundColor: 'rgba(75, 192, 75, 0.5)',
          yAxisID: 'y',
        },
        {
          label: 'Rainfall Anomaly (mm)',
          data: selectedFarmer.history.map(item => item.rainfall_anomaly).reverse(),
          borderColor: 'rgb(53, 162, 235)',
          backgroundColor: 'rgba(53, 162, 235, 0.5)',
          yAxisID: 'y1',
        },
      ],
    };
  };

  const historyChartOptions = {
    responsive: true,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    stacked: false,
    scales: {
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: 'NDVI Value'
        },
        min: -0.1,
        max: 0.9
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'Rainfall Anomaly (mm)'
        }
      },
    },
  };

  if (loading) {
    return (
      <Container className="mt-5 text-center">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
        <p className="mt-2">Loading climate data...</p>
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="mt-5">
        <div className="alert alert-danger">{error}</div>
      </Container>
    );
  }

  return (
    <Container fluid className="mt-4">
      <h1 className="mb-4">Climate Data Dashboard</h1>
      
      {stats && (
        <Row className="mb-4">
          <Col md={4}>
            <Card className="h-100">
              <Card.Header>NDVI Statistics</Card.Header>
              <Card.Body>
                <p>Vegetation Health Index</p>
                <p><strong>Average:</strong> {stats.ndvi.avg?.toFixed(2)}</p>
                <p><strong>Range:</strong> {stats.ndvi.min?.toFixed(2)} to {stats.ndvi.max?.toFixed(2)}</p>
                <div className="mt-3">
                  <div style={{ 
                    height: '20px', 
                    background: 'linear-gradient(to right, brown, yellow, green)',
                    position: 'relative'
                  }}>
                    {stats.ndvi.avg !== undefined && (
                      <div style={{
                        position: 'absolute',
                        left: `${((stats.ndvi.avg + 0.1) / 1.0) * 100}%`,
                        top: 0,
                        width: '3px',
                        height: '20px',
                        backgroundColor: 'black'
                      }} />
                    )}
                  </div>
                  <div className="d-flex justify-content-between">
                    <small>-0.1 (Barren)</small>
                    <small>0.9 (Lush)</small>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={4}>
            <Card className="h-100">
              <Card.Header>Rainfall Anomaly Statistics</Card.Header>
              <Card.Body>
                <p>Deviation from historical average (mm)</p>
                <p><strong>Average:</strong> {stats.rainfall_anomaly.avg?.toFixed(1)}mm</p>
                <p><strong>Range:</strong> {stats.rainfall_anomaly.min?.toFixed(1)}mm to {stats.rainfall_anomaly.max?.toFixed(1)}mm</p>
                <div className="mt-3">
                  <div style={{ 
                    height: '20px', 
                    background: 'linear-gradient(to right, brown, white, blue)',
                    position: 'relative'
                  }}>
                    {stats.rainfall_anomaly.avg !== undefined && (
                      <div style={{
                        position: 'absolute',
                        left: `${((stats.rainfall_anomaly.avg + 50) / 100) * 100}%`,
                        top: 0,
                        width: '3px',
                        height: '20px',
                        backgroundColor: 'black'
                      }} />
                    )}
                  </div>
                  <div className="d-flex justify-content-between">
                    <small>-50mm (Drought)</small>
                    <small>+50mm (Excess)</small>
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={4}>
            <Card className="h-100">
              <Card.Header>Climate Risk Assessment</Card.Header>
              <Card.Body>
                <p><strong>Total Farmers:</strong> {stats.total_farmers}</p>
                
                <div className="mt-3">
                  <h6>Risk Distribution:</h6>
                  {/* Calculate risk distribution */}
                  {(() => {
                    const riskCounts = {
                      LOW: 0,
                      MEDIUM: 0,
                      HIGH: 0,
                      UNKNOWN: 0
                    };
                    
                    climateData.forEach(farmer => {
                      // Reuse logic from serializer to calculate risk
                      let risk = 'UNKNOWN';
                      
                      if (farmer.ndvi_value !== null && farmer.rainfall_anomaly_mm !== null) {
                        let ndviRisk = 0;
                        if (farmer.ndvi_value < 0.1) ndviRisk = 3;
                        else if (farmer.ndvi_value < 0.3) ndviRisk = 2;
                        else ndviRisk = 1;
                        
                        let rainfallRisk = 0;
                        if (Math.abs(farmer.rainfall_anomaly_mm) > 30) rainfallRisk = 3;
                        else if (Math.abs(farmer.rainfall_anomaly_mm) > 15) rainfallRisk = 2;
                        else rainfallRisk = 1;
                        
                        const totalRisk = ndviRisk + rainfallRisk;
                        
                        if (totalRisk >= 5) risk = 'HIGH';
                        else if (totalRisk >= 3) risk = 'MEDIUM';
                        else risk = 'LOW';
                      }
                      
                      riskCounts[risk]++;
                    });
                    
                    return (
                      <>
                        <div className="mb-2">
                          <Badge bg="success">Low: {riskCounts.LOW}</Badge>{' '}
                          <Badge bg="warning">Medium: {riskCounts.MEDIUM}</Badge>{' '}
                          <Badge bg="danger">High: {riskCounts.HIGH}</Badge>{' '}
                          <Badge bg="secondary">Unknown: {riskCounts.UNKNOWN}</Badge>
                        </div>
                        
                        <ProgressBar className="mt-2">
                          <ProgressBar variant="success" now={(riskCounts.LOW / stats.total_farmers) * 100} key={1} />
                          <ProgressBar variant="warning" now={(riskCounts.MEDIUM / stats.total_farmers) * 100} key={2} />
                          <ProgressBar variant="danger" now={(riskCounts.HIGH / stats.total_farmers) * 100} key={3} />
                          <ProgressBar variant="secondary" now={(riskCounts.UNKNOWN / stats.total_farmers) * 100} key={4} />
                        </ProgressBar>
                      </>
                    );
                  })()}
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
      
      <Row>
        <Col md={selectedFarmer ? 6 : 12} className="mb-4">
          <Card className="h-100">
            <Card.Header>Climate Data Map</Card.Header>
            <Card.Body>
              <div style={{ height: '500px', width: '100%' }}>
                <MapContainer center={[-1.9403, 29.8739]} zoom={8} style={{ height: '100%', width: '100%' }}>
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {climateData.map(farmer => (
                    <Marker 
                      key={farmer.id} 
                      position={[farmer.latitude, farmer.longitude]}
                      eventHandlers={{
                        click: () => setSelectedFarmer(farmer)
                      }}
                    >
                      <Popup>
                        <div>
                          <h6>{farmer.name}</h6>
                          <p><strong>Location:</strong> {farmer.location_name}</p>
                          <p><strong>NDVI:</strong> {farmer.ndvi_value?.toFixed(2)}</p>
                          <p><strong>Rainfall Anomaly:</strong> {farmer.rainfall_anomaly_mm?.toFixed(1)}mm</p>
                          <p>
                            <strong>Risk Level:</strong>{' '}
                            <Badge bg={RISK_COLORS[farmer.risk_level]}>{farmer.risk_level}</Badge>
                          </p>
                          <button 
                            className="btn btn-sm btn-primary" 
                            onClick={() => setSelectedFarmer(farmer)}
                          >
                            View Details
                          </button>
                        </div>
                      </Popup>
                    </Marker>
                  ))}
                </MapContainer>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        {selectedFarmer && (
          <Col md={6} className="mb-4">
            <Card className="h-100">
              <Card.Header className="d-flex justify-content-between align-items-center">
                <span>Farmer Climate Details</span>
                <button 
                  className="btn btn-sm btn-outline-secondary" 
                  onClick={() => setSelectedFarmer(null)}
                >
                  Close
                </button>
              </Card.Header>
              <Card.Body>
                <h5>{selectedFarmer.name}</h5>
                <div className="mb-3">
                  <p><strong>Location:</strong> {selectedFarmer.location_name}</p>
                  <p>
                    <strong>Risk Level:</strong>{' '}
                    <Badge bg={RISK_COLORS[selectedFarmer.risk_level]}>{selectedFarmer.risk_level}</Badge>
                  </p>
                  <p><strong>Last Updated:</strong> {new Date(selectedFarmer.last_climate_update).toLocaleString()}</p>
                </div>
                
                <Row className="mb-3">
                  <Col md={6}>
                    <Card>
                      <Card.Body className="text-center">
                        <h6>NDVI Value</h6>
                        <div className="d-flex align-items-center justify-content-center">
                          <div 
                            style={{ 
                              width: '60px', 
                              height: '60px', 
                              borderRadius: '50%', 
                              backgroundColor: getNdviColor(selectedFarmer.ndvi_value),
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'white',
                              fontWeight: 'bold',
                              fontSize: '1.2rem',
                              marginRight: '10px'
                            }}
                          >
                            {selectedFarmer.ndvi_value?.toFixed(2)}
                          </div>
                          <div>
                            {selectedFarmer.ndvi_value < 0.1 && <p>Poor vegetation</p>}
                            {selectedFarmer.ndvi_value >= 0.1 && selectedFarmer.ndvi_value < 0.3 && <p>Moderate vegetation</p>}
                            {selectedFarmer.ndvi_value >= 0.3 && <p>Healthy vegetation</p>}
                          </div>
                        </div>
                      </Card.Body>
                    </Card>
                  </Col>
                  <Col md={6}>
                    <Card>
                      <Card.Body className="text-center">
                        <h6>Rainfall Anomaly</h6>
                        <div className="d-flex align-items-center justify-content-center">
                          <div 
                            style={{ 
                              width: '60px', 
                              height: '60px', 
                              borderRadius: '50%', 
                              backgroundColor: getRainfallColor(selectedFarmer.rainfall_anomaly_mm),
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'white',
                              fontWeight: 'bold',
                              fontSize: '1.2rem',
                              marginRight: '10px'
                            }}
                          >
                            {selectedFarmer.rainfall_anomaly_mm?.toFixed(1)}
                          </div>
                          <div>
                            {selectedFarmer.rainfall_anomaly_mm < -20 && <p>Significant drought</p>}
                            {selectedFarmer.rainfall_anomaly_mm >= -20 && selectedFarmer.rainfall_anomaly_mm < -5 && <p>Mild drought</p>}
                            {selectedFarmer.rainfall_anomaly_mm >= -5 && selectedFarmer.rainfall_anomaly_mm <= 5 && <p>Normal rainfall</p>}
                            {selectedFarmer.rainfall_anomaly_mm > 5 && selectedFarmer.rainfall_anomaly_mm <= 20 && <p>Above average</p>}
                            {selectedFarmer.rainfall_anomaly_mm > 20 && <p>Excessive rainfall</p>}
                          </div>
                        </div>
                      </Card.Body>
                    </Card>
                  </Col>
                </Row>
                
                {selectedFarmer.history ? (
                  <div>
                    <h6 className="mt-3">Climate History (12 Months)</h6>
                    <Line options={historyChartOptions} data={getHistoryChartData()} />
                  </div>
                ) : (
                  <div className="text-center mt-3">
                    <Spinner animation="border" size="sm" /> Loading history...
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>
        )}
      </Row>
      
      <Row className="mb-4">
        <Col>
          <Card>
            <Card.Header>Farmer Climate Data Table</Card.Header>
            <Card.Body>
              <div className="table-responsive">
                <Table striped bordered hover>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Location</th>
                      <th>NDVI Value</th>
                      <th>Rainfall Anomaly</th>
                      <th>Risk Level</th>
                      <th>Last Updated</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {climateData.map(farmer => (
                      <tr key={farmer.id}>
                        <td>{farmer.name}</td>
                        <td>{farmer.location_name}</td>
                        <td>
                          <span 
                            className="badge"
                            style={{ 
                              backgroundColor: getNdviColor(farmer.ndvi_value), 
                              color: 'white' 
                            }}
                          >
                            {farmer.ndvi_value?.toFixed(2)}
                          </span>
                        </td>
                        <td>
                          <span 
                            className="badge"
                            style={{ 
                              backgroundColor: getRainfallColor(farmer.rainfall_anomaly_mm), 
                              color: 'white' 
                            }}
                          >
                            {farmer.rainfall_anomaly_mm?.toFixed(1)} mm
                          </span>
                        </td>
                        <td>
                          <Badge bg={RISK_COLORS[farmer.risk_level]}>
                            {farmer.risk_level}
                          </Badge>
                        </td>
                        <td>{new Date(farmer.last_climate_update).toLocaleString()}</td>
                        <td>
                          <button 
                            className="btn btn-sm btn-primary" 
                            onClick={() => setSelectedFarmer(farmer)}
                          >
                            View Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default ClimateDataDashboard; 