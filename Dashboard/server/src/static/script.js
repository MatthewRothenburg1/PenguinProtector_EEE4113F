let isStreaming = false;

  function toggleStreaming() {
    const button = document.getElementById("streamButton");
    const newState = !isStreaming;

    fetch(`https://flask-fire-837838013707.africa-south1.run.app/set_streaming_state?value=${newState}`, {
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

