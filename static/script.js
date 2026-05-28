const msgsElement = document.getElementById("msgs");

function addMsg(timestamp, user, msg) {
	msgsElement.innerHTML += `
    <span class="msg">
        <span class="timestamp">${timestamp}</span>
        <span class="user">${user}</span>
        <span class="content">${msg}</span>
    </span>`;
}

// connect ws
const socket = new WebSocket("ws://localhost:8000/ws");

socket.addEventListener("open", () => {
	console.log("Connected to ws");

	// send streamer config
	socket.send("[SET_STREAM] bastighg");
});

socket.addEventListener("message", (event) => {
	console.log("ws message:", event.data);
	const [type, timestamp, user, msg] = event.data.split(";");

	if (type === "CHAT_MESSAGE") {
		const time = timestamp.split(" ")[1].split(".")[0];
		addMsg(time, user, msg);
	}
});

socket.addEventListener("error", (error) => {
	console.error("ws error:", error);
});

socket.addEventListener("close", () => {
	console.log("ws connection closed");
});
