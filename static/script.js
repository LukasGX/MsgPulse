const msgsElement = document.getElementById("msgs");
const liveChatElement = document.getElementById("live-chat");

function openModal(content, close = true) {
	const modal = document.createElement("div");
	modal.className = "modal";

	const modalContent = document.createElement("div");
	modalContent.className = "modal-content";
	modalContent.innerHTML = content;

	if (close) {
		const closeButton = document.createElement("span");
		closeButton.className = "close-modal";
		closeButton.innerHTML = "&times;";
		closeButton.onclick = () => {
			closeModal();
		};
	}

	if (close) modalContent.appendChild(closeButton);
	modal.appendChild(modalContent);
	document.body.appendChild(modal);
}

function closeModal() {
	document.querySelectorAll(".modal").forEach((el) => el.remove());
}

function addMsg(timestamp, user, msg) {
	msgsElement.innerHTML += `
    <span class="msg">
        <span class="timestamp">${timestamp}</span>
        <span class="user">${user}</span>
        <span class="content">${msg}</span>
    </span>`;

	liveChatElement.scrollTop = liveChatElement.scrollHeight;
}

async function getAllWords(streamer) {
	const response = await fetch(`/all-words/${streamer}`);

	if (!response.ok) {
		console.error("Failed to fetch all words:", response.statusText);
		return null;
	}

	return await response.json();
}

function updateWordData(wordCounts) {
	// chart
	const sortedWords = Object.entries(wordCounts)
		.sort((a, b) => b[1] - a[1])
		.slice(0, 10);

	mostWordsChart.updateOptions({
		xaxis: {
			categories: sortedWords.map(([word]) => word)
		},
		series: [
			{
				data: sortedWords.map(([_, count]) => count)
			}
		]
	});

	// table
	const rowData = Object.entries(wordCounts).map(([word, count]) => ({
		word,
		count
	}));

	grid.setGridOption("rowData", rowData);
}

// CHARTS
const mostWordsOptions = {
	chart: {
		type: "bar",
		height: 350
	},

	series: [
		{
			name: "Anzahl",
			data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
		}
	],

	xaxis: {
		categories: ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
	}
};

const mostWordsChart = new ApexCharts(
	document.querySelector("#most-words-chart"),
	mostWordsOptions
);

mostWordsChart.render();

// TABLES
const columnDefs = [
	{ field: "word", headerName: "Wort", sortable: true, filter: true },
	{ field: "count", headerName: "Anzahl", sortable: true, sort: "desc" }
];

const gridOptions = {
	columnDefs,
	rowData: [],
	animateRows: true,
	defaultColDef: {
		resizable: true,
		flex: 1
	},
	suppressCellFocus: true
};

const gridDiv = document.querySelector("#all-words-table");

const grid = agGrid.createGrid(gridDiv, gridOptions);

openModal(
	`
	<h2>Streamer auswählen</h2>
	<input type="text" id="streamer-input" placeholder="Twitch-Name">
	<button id="connect-btn">Verbinden</button>
`,
	false
);

document.getElementById("connect-btn").onclick = () => {
	const streamer = document.getElementById("streamer-input").value.trim();

	if (streamer) {
		connectWebSocket(streamer);
		closeModal();
	} else {
		alert("Bitte gib einen Twitch-Streamernamen ein.");
	}
};

function connectWebSocket(streamer) {
	// connect ws
	const socket = new WebSocket("ws://localhost:8000/ws");

	STREAMER = streamer;

	socket.addEventListener("open", async () => {
		console.log("Connected to ws");

		// send streamer config
		socket.send(`[SET_STREAM] ${STREAMER}`);

		// update title
		document.getElementById("lc").textContent = `Live Chat - ${STREAMER}`;

		// initial data fetch
		const initial = await getAllWords(STREAMER);

		if (initial?.words) {
			const wordCounts = Object.fromEntries(initial.words);
			updateWordData(wordCounts);
		}
	});

	socket.addEventListener("message", (event) => {
		console.log("ws message:", event.data);
		const data = JSON.parse(event.data);

		if (data.type == "chat_message") {
			const date = new Date(data.timestamp);
			const time = date.toLocaleTimeString("de-DE", {
				timeZone: "Europe/Berlin",
				hour: "2-digit",
				minute: "2-digit",
				second: "2-digit"
			});
			addMsg(time, data.username, data.content);

			if (data.word_count) {
				const wordCounts = {};
				const pairs = data.word_count.split(";");

				for (const pair of pairs) {
					const [word, count] = pair.split("=");
					wordCounts[word] = parseInt(count);
				}

				updateWordData(wordCounts);
			}
		} else if (data.type == "live_info") {
			const date = new Date(data.live_since);
			const liveSince = date.toLocaleString("de-DE", {
				timeZone: "Europe/Berlin",
				day: "2-digit",
				month: "2-digit",
				year: "numeric",
				hour: "2-digit",
				minute: "2-digit"
			});
			document.querySelector("h1").textContent +=
				` (Läuft seit: ${liveSince})`;
		}
	});

	socket.addEventListener("error", (error) => {
		console.error("ws error:", error);
	});

	socket.addEventListener("close", () => {
		console.log("ws connection closed");
	});
}
