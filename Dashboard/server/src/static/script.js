
const url = "https://flask-fire-837838013707.africa-south1.run.app/";
//const url = "http://127.0.0.1:8080/";

let isStreaming = false;


let detectionStats = {}; // To store fetched data

// Fetch detection stats from API
fetch(`${url}detection_stats`)
  .then(response => {
    if (!response.ok) throw new Error("Failed to fetch detection stats");
    return response.json();
  })
  .then(data => {
    detectionStats = data;
    console.log("Fetched detection stats:", detectionStats); // Log the full data
    updateStatsDisplay();  // Show initial stats right after fetch
  })
  .catch(error => {
    console.error("Error fetching detection stats:", error);
    document.getElementById("stats-display").textContent = "Failed to load stats";
  });

fetch(`${url}get_interaction_time`)
  .then(response => {
    if (!response.ok) throw new Error("Failed to fetch interaction time");
    return response.json();
  })
  .then(data => {
    console.log("Fetched interaction data:", data);

    if (data.interaction_time && data.time_passed) {
      document.getElementById("last-interaction").textContent = data.interaction_time;
      document.getElementById("time-since-last-interaction").textContent = data.time_passed;
    } else {
      document.getElementById("last-interaction").textContent = "No data";
      document.getElementById("time-since-last-interaction").textContent = "N/A";
    }
  })
  .catch(error => {
    console.error("Error fetching interaction time:", error);
    document.getElementById("last-interaction").textContent = "Error";
    document.getElementById("time-since-last-interaction").textContent = "Error";
  });


// Function to update displayed stats based on dropdown selection
function updateStatsDisplay() {
  const select = document.getElementById("analytics-range");
  const selectedRange = select.value;
  const statsDiv = document.getElementById("stats-display");

  if (detectionStats[selectedRange]) {
    const trueCount = detectionStats[selectedRange].true || 0;
    const falseCount = detectionStats[selectedRange].false || 0;
    const total = trueCount + falseCount;
    const falsePercent = total > 0 ? ((falseCount / total) * 100).toFixed(2) : "0.00";

    statsDiv.innerHTML = `
      True detections: ${trueCount} <br>
      False detections: ${falseCount} <br>
      False detections %: ${falsePercent}%
    `;
  } else {
    statsDiv.textContent = "No data available for this period.";
  }
}



// Update stats display when dropdown value changes
document.getElementById("analytics-range").addEventListener("change", updateStatsDisplay);

function toggleStreaming() {
  const button = document.getElementById("streamButton");
  const newState = !isStreaming;

  fetch(`${url}set_streaming_state?value=${newState}`, {
    method: "POST"
  })
  .then(response => {
    if (!response.ok) throw new Error("Failed to update streaming state");
    return response.json();
  })
  .then(data => {
    isStreaming = newState;
    button.textContent = isStreaming ? "Stop Livestream" : "Start Livestream";
    button.style.backgroundColor = isStreaming ? "red" : "";
    button.style.color = isStreaming ? "white" : "";
  })
  .catch(error => {
    console.error("Error:", error);
  });
}
