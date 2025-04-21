import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Navbar, Nav, Container } from 'react-bootstrap';
import ClimateDataDashboard from './components/ClimateDataDashboard';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar bg="dark" variant="dark" expand="lg">
          <Container>
            <Navbar.Brand as={Link} to="/">Farm Finance Platform</Navbar.Brand>
            <Navbar.Toggle aria-controls="basic-navbar-nav" />
            <Navbar.Collapse id="basic-navbar-nav">
              <Nav className="me-auto">
                <Nav.Link as={Link} to="/">Home</Nav.Link>
                <Nav.Link as={Link} to="/farmers">Farmers</Nav.Link>
                <Nav.Link as={Link} to="/loans">Loans</Nav.Link>
                <Nav.Link as={Link} to="/climate">Climate Dashboard</Nav.Link>
              </Nav>
              <Nav>
                <Nav.Link>Login</Nav.Link>
              </Nav>
            </Navbar.Collapse>
          </Container>
        </Navbar>

        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/farmers" element={<p>Farmers list will go here</p>} />
          <Route path="/loans" element={<p>Loans management will go here</p>} />
          <Route path="/climate" element={<ClimateDataDashboard />} />
        </Routes>
      </div>
    </Router>
  );
}

// Simple home component
function Home() {
  return (
    <Container className="mt-5">
      <h1>Farm Finance Platform</h1>
      <p className="lead">
        A comprehensive platform for managing agricultural loans and monitoring climate conditions
      </p>
      <div className="row mt-4">
        <div className="col-md-4 mb-4">
          <div className="card h-100">
            <div className="card-body">
              <h5 className="card-title">Farmer Management</h5>
              <p className="card-text">Register and manage farmers, track their farm details and production.</p>
              <Link to="/farmers" className="btn btn-primary">Manage Farmers</Link>
            </div>
          </div>
        </div>
        <div className="col-md-4 mb-4">
          <div className="card h-100">
            <div className="card-body">
              <h5 className="card-title">Loan Management</h5>
              <p className="card-text">Manage agricultural loans, track repayments, and monitor loan performance.</p>
              <Link to="/loans" className="btn btn-primary">Manage Loans</Link>
            </div>
          </div>
        </div>
        <div className="col-md-4 mb-4">
          <div className="card h-100">
            <div className="card-body">
              <h5 className="card-title">Climate Dashboard</h5>
              <p className="card-text">Monitor climate conditions, track vegetation health, and assess climate risks.</p>
              <Link to="/climate" className="btn btn-primary">View Dashboard</Link>
            </div>
          </div>
        </div>
      </div>
    </Container>
  );
}

export default App; 