import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import fetch from "node-fetch";
// const fs = require("fs");
import fs from "fs";
// const unzipper = require("unzipper");
import unzipper from "unzipper";
// const path = require("path");
import os from "os";
import { exec, spawn } from "child_process";
import dotenv from "dotenv";
import https from "https";
import http from "http";

const basePath = path.join("C:", "Users", "HP", "Documents", "GitHub", "chat_tool", "files", "downloadsHere"); // Windows

// Load environment variables from .env file
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8089;

// Get API key from .env file
const XAI_API_KEY = process.env.secret;
const PROJECT_FOLDER = process.env.PROJECT_FOLDER || path.join(os.homedir(), "Downloads");

const checkPortInUse = (port) => {
  return new Promise((resolve, reject) => {
    exec(`lsof -i :${port}`, (error, stdout, stderr) => {
      if (error) {
        reject(error);
      }
      resolve(stdout);
    });
  });
};

const killProcessOnPort = (port) => {
  return new Promise((resolve, reject) => {
    exec(`lsof -ti :${port} | xargs kill -9`, (error, stdout, stderr) => {
      if (error) {
        reject(`Error killing process: ${stderr}`);
      }
      resolve(stdout);
    });
  });
};

app.use(express.json());
app.use(express.static(__dirname));

// === Routes ===

// index.html
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// static files
app.get("/logo", (req, res) => {
  res.sendFile(path.join(__dirname, "images", "Blue (Gradient).png"));
});

app.get("/gif", (req, res) => {
  console.log("Hi");
  res.sendFile(path.join(__dirname, "images", "0910.gif"));
});

app.get("/fullscreenlogo", (req, res) => {
  res.sendFile(path.join(__dirname, "images", "expand.svg"));
});

// chat endpoint
app.post("/chat", async (req, res) => {
  const { messages } = req.body;
  //console.log(messages);

  if (!messages) {
    return res.status(400).json({ error: "messages array required" });
  }

  const payload = {
    model: "grok-3", // xAI's Grok model
    messages,
    max_tokens: 6000,
    temperature: 0.7,
  };

  try {
    const response = await fetch("https://api.x.ai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${XAI_API_KEY}`,
      },
      body: JSON.stringify(payload),
      timeout: 300000, // 300 seconds
    });

    const text = await response.text();
    res.status(response.status).type("application/json").send(text);
    console.log("Response from /chat:", text);
  } catch (err) {
    console.error(err);
    console.log("Error in /chat route:", err);
    res.status(500).json({ error: "request failed", detail: err.message });
  }
});
app.get("/server-download", async (req, res) => {
  try {
    const fileUrl = `http://localhost:${PORT}/download`;
    const destination = path.join(basePath, "ReactNodeTemplate.zip");

    // Ensure folder exists
    fs.mkdirSync(basePath, { recursive: true });

    const file = fs.createWriteStream(destination);
    const protocol = fileUrl.startsWith("https") ? https : http;

    protocol
      .get(fileUrl, (response) => {
        response.pipe(file);
        file.on("finish", () => {
          file.close();
          console.log("✅ File saved to:", destination);
          res.json({
            success: true,
            message: "File downloaded successfully to server folder",
            path: destination,
          });
        });
      })
      .on("error", (err) => {
        fs.unlink(destination, () => {});
        console.error("Error downloading file:", err);
        res.status(500).json({ success: false, error: err.message });
      });
  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.get("/download", (req, res) => {
  const filePath = path.join(__dirname, "files", "ReactNodeTemplate.zip");
  res.download(filePath, "ReactNodeTemplate.zip", (err) => {
    if (err) {
      console.error("Error while downloading:", err);
    }
  });
});

async function unzipFile(zipPath, extractTo) {
  fs.createReadStream(zipPath)
    .pipe(unzipper.Extract({ path: extractTo }))
    .on("close", () => {
      console.log("Unzip complete!");
    });
}

app.get("/extract", (req, res) => {
  const downloadsPath = basePath;
  console.log("Downloads folderr:", downloadsPath);
  const zipPath = path.join(downloadsPath, "ReactNodeTemplate.zip");
  const extractTo = path.join(PROJECT_FOLDER, "extracted");

  unzipFile(zipPath, extractTo);
});

// Save index.html
app.post("/save-html", (req, res) => {
  const { content } = req.body;
  if (!content) {
    return res.status(400).json({ error: "No content provided" });
  }

  const downloadsPath = path.join(os.homedir(), "Downloads", "extracted", "ReactNodeTemplate");
  fs.mkdirSync(downloadsPath, { recursive: true }); // ensure folder exists

  const filePath = path.join(downloadsPath, "index.html");
  fs.writeFileSync(filePath, content, "utf8");

  res.json({ success: true, path: filePath });
});
app.post("/save-appjsx", (req, res) => {
  const { content } = req.body;
  if (!content) {
    return res.status(400).json({ error: "No content provided" });
  }

  const downloadsPath = path.join(os.homedir(), "Downloads", "extracted", "ReactNodeTemplate", "frontend", "src");
  const savePath = path.join(PROJECT_FOLDER, "extracted", "ReactNodeTemplate", "frontend", "src");

  fs.mkdirSync(savePath, { recursive: true });

  const filePath = path.join(savePath, "App.jsx");
  fs.writeFileSync(filePath, content, "utf8");

  res.json({ success: true, path: filePath });
});

// Save server.js
app.post("/save-serverjs", (req, res) => {
  const { content } = req.body;
  if (!content) {
    return res.status(400).json({ error: "No content provided" });
  }

  const downloadsPath = path.join(os.homedir(), "Downloads", "extracted", "ReactNodeTemplate", "backend");
  const savePath = path.join(PROJECT_FOLDER, "extracted", "ReactNodeTemplate", "backend");

  fs.mkdirSync(savePath, { recursive: true });

  const filePath = path.join(savePath, "server.js");
  fs.writeFileSync(filePath, content, "utf8");

  res.json({ success: true, path: filePath });
});

// Save logicofgame.js
app.post("/save-logicofgamejs", (req, res) => {
  let { content } = req.body;
  console.log("content");
  if (!content) {
    return res.status(400).json({ error: "No content provided" });
  }

  const downloadsPath = path.join(os.homedir(), "Downloads", "extracted", "ReactNodeTemplate", "backend");
  const savePath = path.join(PROJECT_FOLDER, "extracted", "ReactNodeTemplate", "backend");

  fs.mkdirSync(savePath, { recursive: true });

  const filePath = path.join(savePath, "logicofgame.js");
  fs.writeFileSync(filePath, content, "utf8");

  res.json({ success: true, path: filePath });
});

app.get("/start-server", async (req, res) => {
  console.log("called start-server route");

  const frontendPort = 5173; // Fixed frontend port
  const backendPort = 8087;  // Backend port (use your existing port)

  const backendPath = path.join(PROJECT_FOLDER, "extracted", "ReactNodeTemplate", "backend");
  const frontendPath = path.join(PROJECT_FOLDER, "extracted", "ReactNodeTemplate", "frontend");

  try {
    // Check and stop frontend server if already running
    try {
      await checkPortInUse(frontendPort);
      console.log(`Frontend server is running on port ${frontendPort}. Stopping the existing server...`);
      await killProcessOnPort(frontendPort);
    } catch (error) {
      console.log(`No existing frontend server found on port ${frontendPort}.`);
    }

    // Check and stop backend server if already running
    try {
      await checkPortInUse(backendPort);
      console.log(`Backend server is running on port ${backendPort}. Stopping the existing server...`);
      await killProcessOnPort(backendPort);
    } catch (error) {
      console.log(`No existing backend server found on port ${backendPort}.`);
    }

    // Install frontend dependencies
    exec("npm install", { cwd: frontendPath }, (error2, stdout2, stderr2) => {
      if (error2) {
        console.error(`Error installing frontend dependencies: ${error2.message}`);
        return;
      }
      if (stderr2) console.error(`stderr: ${stderr2}`);
      console.log(`stdout: ${stdout2}`);
      console.log("Frontend dependencies installed successfully");

      // Start frontend server using spawn (for long-running process)
      const frontendProcess = spawn("npm", ["run", "dev"], { cwd: frontendPath, shell: true });
      
      frontendProcess.stdout.on('data', (data) => {
        console.log(`Frontend: ${data}`);
      });
      
      frontendProcess.stderr.on('data', (data) => {
        console.error(`Frontend Error: ${data}`);
      });
      
      frontendProcess.on('spawn', () => {
        console.log("✅ Frontend server started successfully on port", frontendPort);
      });
    });

    // Install backend dependencies
    exec("npm install", { cwd: backendPath }, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error installing dependencies: ${error.message}`);
        return;
      }
      if (stderr) console.error(`stderr: ${stderr}`);
      console.log(`stdout: ${stdout}--`);

      // Start backend server using spawn (for long-running process)
      const backendProcess = spawn("npm", ["start"], { cwd: backendPath, shell: true });
      
      backendProcess.stdout.on('data', (data) => {
        console.log(`Backend: ${data}`);
      });
      
      backendProcess.stderr.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
      });
      
      backendProcess.on('spawn', () => {
        console.log("✅ Backend server started successfully on port", backendPort);
      });
    });

    // Send response immediately (servers will start in background)
    res.send("Both servers are starting! Check console logs for status.");
  } catch (error) {
    console.error("Error:", error);
    res.status(500).send("Failed to start server(s)");
  }
});

app.get("/delete", (req, res) => {
  const downloadsPath = path.join(os.homedir(), "Downloads");

  const zipPath = path.join(downloadsPath, "ReactNodeTemplate.zip");
  const extractTo = path.join(downloadsPath, "extracted");

  // 2️⃣ Delete the zip file
  fs.unlink(zipPath, (err) => {
    if (err) {
      console.error("Failed to delete zip:", err);
      return res.status(500).send("Extracted, but failed to delete zip");
    }
    console.log("Deleted zip:", zipPath);

    // 3️⃣ Delete the extracted folder (recursively)
    fs.rm(extractTo, { recursive: true, force: true }, (err) => {
      if (err) {
        console.error("Failed to delete extracted folder:", err);
        return res.status(500).send("Zip deleted, but failed to delete folder");
      }
      console.log("Deleted extracted folder:", extractTo);

      res.send("Extracted, then deleted zip and folder successfully!");
    });
  });
});

let gameSessionUuid = 218;
app.post("/get2links", (req, res) => {
  gameSessionUuid = gameSessionUuid + 1;
  try {
    // Example static request data (you could replace this with actual data from DB or body)
    const request = {
      room: {
        name: "ProductionRoom",
        gameSessionUuid: gameSessionUuid,
        coinBetAmount: 50,
      },
      players: [
        {
          name: "Player1",
          uuid: "uuid_1",
          profileImage: "https://safa.sgp1.digitaloceanspaces.com/safa./avatar_images/Kaelani_M.png",
          ready: true,
        },
        {
          name: "Player2",
          uuid: "uuid_2",
          profileImage: "https://safa.sgp1.digitaloceanspaces.com/safa./avatar_images/Zayven_M.png",
          ready: true,
        },
      ],
    };

    const baseUrl = "https://aigamef.gameonworld.ai";
    const gameStateId = "68f5bddd86748a2b6dfa746c"; // mock ID, you can replace dynamically

    const payload = {
      gameSessionUuid: request.room.gameSessionUuid,
      gameStateId,
      name: request.room.name,
      createDate: new Date().toISOString(),
      link1: `${baseUrl}/?gameSessionUuid=${request.room.gameSessionUuid}&gameStateId=${gameStateId}&uuid=${request.players[0].uuid}`,
      link2: `${baseUrl}/?gameSessionUuid=${request.room.gameSessionUuid}&gameStateId=${gameStateId}&uuid=${request.players[1].uuid}`,
    };

    return res.json({
      status: true,
      message: "success",
      payload,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      status: false,
      message: "error generating links",
    });
  }
});

// // // Example: unzip archive.zip into ./extracted
// const downloadsPath = path.join(os.homedir(), "Downloads");
// console.log("Downloads folderr:", downloadsPath);

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
