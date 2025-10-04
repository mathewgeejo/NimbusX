import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const ProbabilityChart = ({ probabilities }) => {
  // Professional label mapping
  const labelMap = {
    'very_hot': 'Extreme Heat',
    'very_cold': 'Extreme Cold',
    'very_wet': 'Heavy Precipitation',
    'very_windy': 'Strong Winds',
    'very_uncomfortable': 'Heat Discomfort'
  };
  
  // Prepare data for chart
  const labels = Object.keys(probabilities).map(key => 
    labelMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  );
  
  const values = Object.values(probabilities);

  // Color code based on probability
  const backgroundColors = values.map(value => {
    if (value >= 70) return 'rgba(239, 68, 68, 0.8)'; // red
    if (value >= 40) return 'rgba(251, 191, 36, 0.8)'; // yellow
    return 'rgba(16, 185, 129, 0.8)'; // green
  });

  const borderColors = values.map(value => {
    if (value >= 70) return 'rgba(239, 68, 68, 1)';
    if (value >= 40) return 'rgba(251, 191, 36, 1)';
    return 'rgba(16, 185, 129, 1)';
  });

  const data = {
    labels: labels,
    datasets: [
      {
        label: 'Probability (%)',
        data: values,
        backgroundColor: backgroundColors,
        borderColor: borderColors,
        borderWidth: 2,
        borderRadius: 8,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `Probability: ${context.parsed.y.toFixed(1)}%`;
          }
        },
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        cornerRadius: 8,
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: function(value) {
            return value + '%';
          },
          font: {
            size: 12,
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
      x: {
        ticks: {
          font: {
            size: 11,
          }
        },
        grid: {
          display: false,
        }
      }
    },
  };

  return (
    <div className="w-full h-64 md:h-80">
      <Bar data={data} options={options} />
    </div>
  );
};

export default ProbabilityChart;
