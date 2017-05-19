EMPTY_NM = 0;
WHITE_NM = 1
BLACK_NM = 2;

EMPTY_CH = '.';
WHITE_CH = 'o';
BLACK_CH = '@';

EMPTY_CO = '#117711';
WHITE_CO = '#ffffff';
BLACK_CO = '#000000';
BORDER_CO = '#663300';

WHITE_IMG = new Image();
WHITE_IMG.src = './images/white.png';
BLACK_IMG = new Image();
BLACK_IMG.src = './images/black.png';

CH2NM = {};
CH2NM[EMPTY_CH] = EMPTY_NM;
CH2NM[WHITE_CH] = WHITE_NM;
CH2NM[BLACK_CH] = BLACK_NM;

NM2CO = [];
NM2CO[EMPTY_NM] = EMPTY_CO;
NM2CO[WHITE_NM] = WHITE_CO;
NM2CO[BLACK_NM] = BLACK_CO;

YELLOW_CO = '#fff700';

function drawBoard(rCanvas, bSize, bArray, tomove){
  if(bSize === rCanvas.bSize) {
    for(var i=0; i<bSize*bSize; i++){
      rCanvas.board[i].fill = NM2CO[bArray[i]];
    }
  } else {
    var bdWidth = rCanvas.rWidth/(11*bSize+1); //from sq*s+bd*(s+1)=w, sq=10*bd
    var bdHeight = rCanvas.rHeight/(11*bSize+1);
    var bd = Math.min(bdWidth,bdHeight);
    var rc = Math.min(rCanvas.rWidth,rCanvas.rHeight);
    var sq = 10*bd;
    var un = bd+sq;

    rCanvas.bd = bd;
    rCanvas.sq = sq;
    rCanvas.un = un;

    rCanvas.objects = [];
    rCanvas.add(new RRect(0,0,rCanvas.rWidth,rCanvas.rHeight,EMPTY_CO));

    for(var i=0; i<=bSize; i++){
      rCanvas.add(new RRect(un*i, 0, bd, rc,BORDER_CO));
      rCanvas.add(new RRect(0, un*i, rc, bd,BORDER_CO));
    }

    rCanvas.board = [];

    for(var y=0; y<bSize; y++){
      for(var x=0; x<bSize; x++){
        var index = bSize*y+x;
        var toAdd;
        if (bArray[index]===EMPTY_NM){
          toAdd = new RRect(un*x+bd, un*y+bd, sq, sq, EMPTY_CO);
        }
        else if (bArray[index]===WHITE_NM) {
          toAdd = new RImg(un*x+bd, un*y+bd, sq, sq, WHITE_IMG);
        }
        else if (bArray[index]===BLACK_NM) {
          toAdd = new RImg(un*x+bd, un*y+bd, sq, sq, BLACK_IMG);
        }
        rCanvas.add(toAdd);
        rCanvas.board[index] = toAdd;
      }
    }
    rCanvas.add(rCanvas.select);
    rCanvas.add(new RRect(0,rCanvas.rWidth,rCanvas.rWidth,rCanvas.rHeight-rCanvas.rWidth,'#808080'));
    rCanvas.add(rCanvas.black);
    rCanvas.add(rCanvas.white);
  }
  // add code to show player scores as well
  var bCount = 0;
  var wCount = 0;
  for(var i=0; i<bArray.length; i++){
    if(bArray[i]==1){wCount++;}
    if(bArray[i]==2){bCount++;}
  }
  rCanvas.black.text = rCanvas.black.text.split(':')[0]+': '+bCount.toString();
  rCanvas.white.text = rCanvas.white.text.split(':')[0]+': '+wCount.toString();
  if(tomove === BLACK_CH){
    rCanvas.black.text = '('+rCanvas.black.text+')';
  }
  else if(tomove === WHITE_CH){
    rCanvas.white.text = '('+rCanvas.white.text+')';
  }
  rCanvas.draw();
  rCanvas.lBSize = bSize;
}

function bStringToBArray(bString){
  bString = bString.replace(/\?/g, '');
  var bArray = [];
  for(var i=0; i<bString.length; i++){
      bArray[i] = CH2NM[bString.charAt(i)];
  }
  return bArray;
}

function resize(canvas, gWidth, gHeight){
  var availWidth = canvas.parentNode.offsetWidth*9/10;
  var availHeight = (window.innerHeight - canvas.parentNode.offsetTop)*9/10;
  if(availWidth*gHeight < availHeight*gWidth){
    canvas.width = availWidth;
    canvas.height = canvas.width * gHeight / gWidth;
  }
  else{
    canvas.height = availHeight;
    canvas.width = canvas.height * gWidth / gHeight;
  }
}

function init(socket, delay, port1, port2, timelimit){
  document.getElementById('canvasContainer').innerHTML =
    '<canvas id="canvas" width="890" height="1000"></canvas>';

  var canvas = document.getElementById('canvas');
  var gWidth = canvas.width;
  var gHeight = canvas.height;

  resize(canvas, gWidth, gHeight);
  var rCanvas = new RCanvas(canvas, gWidth, gHeight);

  var gap = rCanvas.rHeight - rCanvas.rWidth;
  rCanvas.black = new RText(0,rCanvas.rHeight-gap*2/5,'Black',gap*2/5,'Roboto Mono',BLACK_CO);
  rCanvas.white = new RText(rCanvas.rWidth/2,rCanvas.rHeight-gap*2/5,'White',gap*2/5,'Roboto Mono',WHITE_CO);

  var selected = new RRect(0, 0, 1, 1, YELLOW_CO);
  rCanvas.select = selected;
  // I'm too lazy to define transparency in the class
  selected.draw  = function(ctx, wFactor, hFactor){
    ctx.fillStyle = this.fill;
    ctx.globalAlpha=0.4;
    ctx.fillRect(this.x*wFactor, this.y*hFactor, this.width*wFactor, this.height*hFactor);
    ctx.globalAlpha=1.0;
  };

  drawBoard(rCanvas,13,[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 2, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 2, 2, 1, 2, 2, 1, 2, 2, 1, 1, 2, 2, 1, 2, 2, 1, 2, 2, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1, 2, 2, 1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1, 1, 2, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1,1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]);

  window.addEventListener('resize', function(){
    resize(canvas, gWidth, gHeight);
    rCanvas.resize();
  });
  document.addEventListener('mousemove', function(event){
    rCanvas.handleMouseMove(event);
    var cy = Math.floor(rCanvas.my / rCanvas.un);
    var cx = Math.floor(rCanvas.mx / rCanvas.un);
    var ox = selected.x;
    var oy = selected.y;
    selected.x = rCanvas.un*cx+rCanvas.bd;
    selected.y = rCanvas.un*cy+rCanvas.bd;
    selected.width = rCanvas.sq;
    selected.height = rCanvas.sq;
    if(ox !== selected.x || oy !== selected.y){
      rCanvas.draw();
    }
  });
  document.addEventListener('mouseup', function(){rCanvas.handleMouseUp();});
  document.addEventListener('mousedown',function(){rCanvas.handleMouseDown();});

  rCanvas.resize();
  socket.emit('prequest',{black:port1,white:port2,tml:timelimit});
  socket.on('reply', function(data){
    rCanvas.black.text = data.black;
    rCanvas.white.text = data.white;
    drawBoard(rCanvas, parseInt(data.bSize), bStringToBArray(data.board), data.tomove);
  });
  rCanvas.clickEvent = function(){
    var olc = this.lastClicked;
    var cy = Math.floor(rCanvas.my / rCanvas.un);
    var cx = Math.floor(rCanvas.mx / rCanvas.un);
    if (cx >= 0 && cx < rCanvas.lBSize && cy >= 0 && cy < rCanvas.lBSize){
      this.lastClicked = cy * (this.lBSize+2) + cx + 3 + this.lBSize;
    }
    if (olc === -1){
      console.log('sent move '+rCanvas.lastClicked);
      socket.emit('movereply', {move:rCanvas.lastClicked.toString()});
    }
  };

  socket.on('moverequest', function(){
    console.log('move requested');
    rCanvas.lastClicked = -1;
  });
  window.setInterval(function(){socket.emit('refresh',{});console.log('refreshed');}, delay);
}

function makeSocketFromPage(addr, port, port1, port2, delay, timelimit){
  var socket = io('https://'+addr+':'+port,{path:'/othello/socket.io/'});
  console.log('made socket');
  var delay = parseInt(delay);
  init(socket, delay, port1, port2, timelimit);
  console.log('finished initing socket');
}