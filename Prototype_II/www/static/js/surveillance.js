/*

    Module: surveillance.js
    Purpose: Called by recorded_videos.html and provides the following functions
    - Menu Control and changing of menus
    - Calendar Navigation for month (previous and next)
    - Calendar Creation and population of each day's # of videos (based on json file sent back from server)
    - Population of each hour on # of videos
    - Interacts with <VIDEO> tag to populate and automatically play the video.


*/


// Hide Live Content - this is intentionally left blank for future enhancements
function hideLiveContent() {


}

// part of menu navigation:
// show Live Content - hides the recorded div tag, if it is visible, hides other info tag if it is visible.
function showLiveContent() {
    hideOtherInfoContent();
    hideRecordedVideoContent();

}

// Menu Control:  to show recorded content and hide other Divs.
function showRecordedVideoContent() {
    // Hide Calendar
        var calendar_list = d3.select("#calendar");
        calendar_list.attr("class","calendar");            
    // show video list
        var video_list_container = d3.select("#video_list_container");
        video_list_container.attr("class","video-list-container");           
        
        hideOtherInfoContent();
        hideLiveContent();


    
}

// Menu Control: Hide Recorded Video tags when the focus is on another menu item.
function hideRecordedVideoContent() {
    var calendar_list = d3.select("#calendar");
    calendar_list.attr("class","calendar-hidden");
    var video_list_container = d3.select("#video_list_container");
    video_list_container.attr("class","video-list-container-hidden");
    
}

// Menu Control: How Other Info Content - if the menu item is clicked
// Hides other divs
function showOtherInfoContent() {
    hideLiveContent();
    hideRecordedVideoContent();
    var other_info = d3.select("#other_info_container");
    other_info.attr("class","other-info-container");


}// Menu Control:  Hide Other Info divs.
function hideOtherInfoContent() {
            // hide other info
    var other_info = d3.select("#other_info_container");
    other_info.attr("class","other-info-container-hidden");

}

// Menu Control: changeMenu Function for menu control.
function changeMenu(menuId) {
    active_menu = d3.select("#" + activeMenuId);
    active_menu.attr("class","menu_cell");
    curr_menu = d3.select("#" + menuId);
    curr_menu.attr("class","menu_cell cell-red");
    activeMenuId = menuId ;

    if(menuId == "menu_live") {

        showLiveContent();
        var video_area =document.getElementById("video_play_area");


        var hls = new Hls({ debug: false});
        var random_var = Math.random().toString();
        hls.loadSource("http://192.168.1.23/surveillance/static/stream/playlist.m3u8?"+random_var);
        hls.attachMedia(video_area);
        
        hls.on(Hls.Events.MEDIA_ATTACHED, function () {
            video_area.muted = true;
            video_area.play();
        });

    } else if(menuId == "menu_recorded_videos") {
        var video = d3.select("#video_play_area")
        video.remove();
        var video_container = d3.select("#video_play");
        video_container.append("video").attr("class","video_play").attr("id","video_play_area").attr("controls","true").attr("autoplay","true")
        showRecordedVideoContent()

        

    } else if(menuId == "menu_other_info") {
        window.location = "admin_login";
    }

}

// Calendar Contro: Decrease Month and initiates create calendar for that month
function decreaseMonth() {
    
    param_year = new Date(param_year, param_month - 1, 1).getFullYear();
    param_month = new Date(param_year, param_month - 1, 1).getMonth();
    createCalendar(param_year, param_month)
}

// Calendar Contro: Increase Month and initiates create calendar for that month
function increaseMonth() {
    param_year = new Date(param_year, param_month + 1, 1).getFullYear();
    param_month = new Date(param_year, param_month + 1, 1).getMonth();
    createCalendar(param_year, param_month)
    
}


// get main calendar container
// // Calendar Contro: Decrease Month and initiates create calendar for that month
// Main function to re-fresh calendar
function createCalendar(year, month) {
    let curr_date = new Date();
    

    // Get the first day of the month
    let dayone = new Date(year, month, 1).getDay();

    let date_one = new Date(year, month, 1);
    let monthName = months[month]

    // Get the last date of the month
    let lastdate = new Date(year, month + 1, 0).getDate();

    // Get the day of the last date of the month
    let dayend = new Date(year, month, lastdate).getDay();

    // Get the last date of the previous month
    let monthlastdate = new Date(year, month, 0).getDate();
    var calendar_parent = d3.select("#calendar")
    var calendar_container = d3.select("#calendar_container")
    calendar_container.remove()

    calendar_container = calendar_parent.append("div").attr("class","calendar-container").attr("id","calendar_container")

    // Add Month
    calendar_container.append("div").attr("class","calendar-month-head").text(monthName + " " + year)
    var prev_button = calendar_container.append("div").attr("class","calendar-week-head-nav").text("Prev")
    var next_button = calendar_container.append("div").attr("class","calendar-week-head-nav").text("Next")
    prev_button.on("click", function(d) {
        decreaseMonth();
    })
    next_button.on("click", function(d) {
        increaseMonth();
    })
    for(var i=0; i<weekName.length; i++) {
        calendar_container.append("div").attr("class","calendar-week-head").text(weekName[i])
    }


    cell_no = dayone % 7 ;
    new_date = date_one;
    
    
    // Create Calendar Header
    new_date.setDate(new_date.getDate() - cell_no - 1)

    // create previous month days
    for(var i=0; i<cell_no; i++) {
        new_date.setDate(new_date.getDate() + 1 )
        
        day_num = new_date.getDate();
        calendar_container.append("div").attr("class","calendar-cell-non-current").text(day_num);
    }

    // create current month - first row only
    for(var i=0; i<(7- cell_no); i++) {
        new_date.setDate(new_date.getDate() + 1 )
        day_num = new_date.getDate();
        var div_day = calendar_container.append("div")
        var cell_grid = div_day.append("div").attr("class","calendar-cell-grid-header").text(day_num)

        date_str = new_date.getFullYear().toString() + "-"+ (new_date.getMonth()+1).toString().padStart(2,"0") + "-"+ new_date.getDate().toString().padStart(2,"0")             
        total_videos = videos_month[date_str];
        total_videos = (total_videos == null) ? 0 : total_videos;

        var cell_style=""
        var cell_style_2 = "calendar-cell-grid-cell"
        if(new_date.getDate() == curr_date.getDate() && 
                new_date.getMonth() == curr_date.getMonth() && 
                new_date.getFullYear() == curr_date.getFullYear()) {
            cell_style = "calendar-cell-curr-day";
            cell_style_2 = "calendar-cell-grid-cell-currday";
        } else {
            if(new_date.getDate() == param_dom && 
                new_date.getMonth() == param_month && 
                new_date.getFullYear() == param_year) {
            cell_style = "calendar-cell-selected-day";
            cell_style_2 = "calendar-cell-grid-cell-selectedday";
                }
    
            }

        var cell_grid_total = cell_grid.append("div").attr("class",cell_style_2).text(total_videos);
        cell_grid_total.attr("onclick","updateParameters(" + new_date.getFullYear().toString() + "," + new_date.getMonth() + "," +  new_date.getDate() + ")")
    }

    // create current month for rest of days - 4 rows - will over flow to next month
    for(var x=0; x<=4;x++) {
        for(y=0;y<7;y++) {

            new_date.setDate(new_date.getDate() + 1 )
            //console.log("[" + new_date.getDate().toString() + "|" + param_dom.toString() + "][" + new_date.getMonth().toString() + "|" + param_month.toString() + "][" +new_date.getFullYear().toString() + "|" + param_year.toString()+ "]");
            day_num = new_date.getDate();
            var cell_style=""
            var cell_style_2 = "calendar-cell-grid-cell"
            if(new_date.getDate() == curr_date.getDate() && 
                    new_date.getMonth() == curr_date.getMonth() && 
                    new_date.getFullYear() == curr_date.getFullYear()) {
                cell_style = "calendar-cell-curr-day";
                cell_style_2 = "calendar-cell-grid-cell-currday";
            } else {
                if(new_date.getDate() == param_dom && 
                    new_date.getMonth() == param_month && 
                    new_date.getFullYear() == param_year) {
                cell_style = "calendar-cell-selected-day";
                cell_style_2 = "calendar-cell-grid-cell-selectedday";
                    }

                if(month != new_date.getMonth()) {
                    cell_style= "calendar-cell-non-current";
                } else {
                    cell_style= "calendar-cell-grid-header";
                }
                
            }

            // calendar_container.append("div").attr("class",cell_style).text(day_num);
            var div_day = calendar_container.append("div").attr("class",cell_style)
            //var cell_grid = div_day.append("div").attr("class","calendar-cell-grid-header").text(day_num)
            var cell_grid = div_day.append("div").text(day_num)
            date_str = new_date.getFullYear().toString() + "-"+ (new_date.getMonth()+1).toString().padStart(2,"0") + "-"+ new_date.getDate().toString().padStart(2,"0")             
            total_videos = videos_month[date_str];
            total_videos = (total_videos == null) ? 0 : total_videos;

            var cell_grid_total = cell_grid.append("div").attr("class",cell_style_2).text(total_videos);
            cell_grid_total.attr("onclick","updateParameters(" + new_date.getFullYear().toString() + "," + new_date.getMonth() + "," +  new_date.getDate() + ")")

        }

    }

}



// // Calendar Control: Creates Video List by the parameter passed in  hour.
function createVideoList(hour) {

    // Set Hoour in focus
    curr_hour = hour

    // Get the main video listing container
    var video_list_container = d3.select("#video_list_container");
    var video_main = d3.select("#video_list_main");

    // Clear all child tags under it.
    video_main.remove();

    // Re Create video list container
    video_main = video_list_container.append("div").attr("id","video_list_main")

    // Add Div to hold hours.
    var hour_grid = video_main.append("div").attr("class","hour-grid")
    hour_grid.append("div").attr("class","hour-grid-bold").text("AM")
    timegrid_arr = []

    // Build the Hourly grid.
    /// 1st Band is the AM band for videos in morning
    for(var i=0;i<12;i++) {
        var timegrid = hour_grid.append("div").attr("onclick","createVideoList(" + i + ")")
        var hour_list = videos[i.toString()]
        var total_videos = videos_hour[i.toString().padStart(2,"0")];
        total_videos = (total_videos == null) ? 0 : total_videos;
        if(i == hour) {
            timegrid.attr("class","hour-grid-cell-selected").html(i.toString().padStart(2,"0") + "<br>" + ((total_videos == 0) ? "-" : total_videos.toString()))
            
        } else {
            timegrid.attr("class","hour-grid-cell").html(i.toString().padStart(2,"0") + "<br>" + ((total_videos == 0) ? "-" : total_videos.toString()))
        }
        
    }
    hour_grid.append("div").attr("class","hour-grid-bold").text("PM")
    // 2nd Band is the PM band for all videos in afternoon and night.
    for(var i=12;i<24;i++) {
        var hour_list = videos[i.toString()]
        var total_videos = videos_hour[i.toString().padStart(2,"0")];
        total_videos = (total_videos == null) ? 0 : total_videos;

        var timegrid = hour_grid.append("div").attr("onclick","createVideoList(" + i + ")")
        if(i == hour ) {
            timegrid.attr("class","hour-grid-cell-selected").html(i.toString() + "<br>" + ((total_videos == 0) ? "-" : total_videos.toString()))
        } else {
            timegrid.attr("class","hour-grid-cell").html(i.toString() + "<br>" +( (total_videos == 0) ? "-" : total_videos.toString()))
        }
        
    }
        refreshMins(param_year, param_month, param_dom, curr_hour);

    

}

// Refresh Calendar calls the server to get list of videos of that day.
// and calls createCalendar to refresh the calendar values.
function refreshCalendar() {
    url = "/surveillance/list_videos_by_day?year" + param_year + "&month" + param_month + "&day" + param_dom
    
    d3.json(url).then(function(element) {
        videos_month = element
        createCalendar(param_year, param_month);
        refreshHour();
        
        
    })

}

// Refresh Hour - provides list of videos for that day by the hour.
function refreshHour() {
    
    url = "/surveillance/list_videos_by_day_hour?year=" + param_year + "&month=" + (param_month+1) + "&day=" + param_dom
    d3.json(url).then(function(element) {
        videos_hour= element
        //createHourlyList(param_year, param_month, day);
        createVideoList(curr_hour);
        
    })
}

// Refresh Mins - Provides list of videos for that day and hour - by the hour.
function refreshMins(param_year, param_month, param_dom, curr_hour) {
    url = "/surveillance/list_videos_by_hour_mins?year=" + param_year + "&month=" + (param_month+1) + "&day=" + param_dom + "&hour=" + curr_hour
    d3.json(url).then(function(element) {
        videos= element
        //createHourlyList(param_year, param_month, day);
        
        createVideoListByMin(curr_hour);
        
    })

}

function createVideoListByMin() {
    el_carousel_container = d3.select("#carousel-container")
    el_carousel_container.selectAll("*").remove()
    carousel_step_value = 0;
    var carousel_hour = d3.select("#carousel_hour");
    carousel_hour.selectAll("*").remove();

    console.log(videos.length);
    if(Object.entries(videos).length == 0) {
        el_carousel_container.append("div").text("No Videos found")
        
    }
    for(var i=-1; i< 61; i++) {
        carousel_hour.append("div").attr("id","min_" + i.toString());
    }    
    var pic_step = 0 
    for(var i=0; i<60; i+=5) {
        
        //video_list.append("div").attr("class","video-list-time").text(parseInt(curr_hour).toString().padStart(2,"0") + ":" + i.toString().padStart(2,"0") );
        hour_list = videos[i];
        
        if(hour_list == null) {
            //video_list.append("div").attr("class","video-list-content").text(" ")
            //el_carousel_container.text("No Videos found")
        } else {
            video_items = hour_list
            video_items.forEach(element => {
                    image_file = element['filename'].replace("raw_capture_","img_").replace(".mp4",".jpg")
                    var el_container_child = el_carousel_container.append("div").attr("class","carousel-item-container").attr("id",element['filename'])
                    var el_container_child_1 = el_container_child.append("div").attr("class","carousel-item")
                    el_container_child_1.append("img").attr("src","/surveillance/static/recorded_images/" + image_file).attr("width", 640).attr("height", 360)
                    el_container_child_1.append("div").text(element['comment'])
                    el_container_child.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")

                    var pic_date_id = "min_" + (new Date(element['date'])).getMinutes().toString() ;
                    var pic_date_el = d3.select("#" + pic_date_id)
                    pic_date_el.attr("style","background-color: #FF0000; width: 10px; height: 10px; justify-self: center;margin: 3px; cursor: pointer")
                    pic_date_el.attr("pic_step",pic_step)
                    pic_date_el.attr("onclick","scrollPicStep(" + pic_step.toString() + ")")
                    pic_step++;

                    
                    
        });
    }

    var el = document.getElementById("carousel-container");
    el.scrollLeft += 0 - (carousel_step_value * 660);
}


    // // dot at the top if there is a video
    // for(var i=-1; i<= 61; i++) {
    //     //var el_min_tag = carousel_hour.append("div");
    //     if(i>=0 && videos[i] != null) {
    //         //var el_min_parent = el_min_tag.append("div").attr("style","border: 1px solid green;align-items: center; justify-self: center;")
    //         var el_min_parent = carousel_hour.append("div").attr("style","align-items: center; justify-self: center;")
    //         el_min_parent.append("div").attr("style","height:10px; width:10px; background-color: #FF0000; border-radius: 10px; cursor: pointer; margin: 10px; padding: 3px;")

    //     } else {
    //         var el_min_parent = carousel_hour.append("div")
            
            

    //     }
        
    //}    
    for(var i=-1; i< 61; i++) {
        //var el_min_tag = carousel_hour.append("div");
        if(i>=0) {
            //var el_min_parent = el_min_tag.append("div").attr("style","border: 1px solid green;align-items: center; justify-self: center;")
            var el_min_parent = carousel_hour.append("div").attr("style","border: 1px solid green;align-items: center; justify-self: center;")
            if((i%5) == 0) {
                el_min_parent.append("div").attr("style","height:20px; width:2px; background-color: #000000;")
            } else {
            
                el_min_parent.append("div").attr("style","height:10px; width:2px; background-color: #000000;")

            }

        } else {
            var el_min_parent = carousel_hour.append("div");
        }
        
    }
    var hour=curr_hour;
    for(var i=1;i<61; i+=5) {
        var el_time = carousel_hour.append("div").attr("style","grid-column: " + i.toString() + "/" + (i+3).toString() + ";font-size: 12px; justify-self: center; ")
        var hour_string = ""
        if(i != 61) {
            hour_string = hour.toString() + ":" + (i-1).toString().padStart(2,'0')
        }
        el_time.append("div").attr("style","text-align: center; padding: 5px; border: 1px solid #000000; border-radius: 5px; margin: 2px;").text(hour_string)
        carousel_hour.append("div")
        carousel_hour.append("div")
        //carousel_hour.append("div")
        //carousel_hour.append("div")
    }

}



// This function re-draws the grid that holds information for all the videos.
function createVideoListByMin1() {


    var video_main = d3.select("#video_list_main")
    var video_list = video_main.append("div").attr("class", "video-list-main")
    video_list.append("div").attr("class","video-list-time").text("Time Slot");
    var title_item_div = video_list.append("div").attr("class","video-list-content-grid")
    title_item_div.append("div").attr("class","video-list-content-item").text("Time")
    title_item_div.append("div").attr("class","video-list-content-item").text("Title")
    title_item_div.append("div").attr("class","video-list-content-item").text("Duration")
    title_item_div.append("div").attr("class","video-list-content-item").text("Size")
    title_item_div.append("div").attr("class","video-list-content-item").text("Comment")

    
    for(var i=0; i<60; i+=5) {
        
        video_list.append("div").attr("class","video-list-time").text(parseInt(curr_hour).toString().padStart(2,"0") + ":" + i.toString().padStart(2,"0") );
        hour_list = videos[i];
        if(hour_list == null) {
            video_list.append("div").attr("class","video-list-content").text(" ")
        } else {
            video_items = hour_list
            if(video_items != null) {
                var item_div = video_list.append("div").attr("class","video-list-content-grid")
                video_items.forEach(element => {
                    image_file = element['filename'].replace("raw_capture_","img_").replace(".mp4",".jpg")
                    var e1 = item_div.append("div").attr("class","video-list-content-item").text(element["time"])
                    var e2 = item_div.append("div").attr("class","video-list-content-item").text(element["title"])
                    var e3 = item_div.append("div").attr("class","video-list-content-item").text(element["duration"])
                    var e4 = item_div.append("div").attr("class","video-list-content-item").text(element["file_size"])
                    var e5 = item_div.append("div").attr("class","video-list-content-item").text(element["comment"])
                    var e6 = item_div.append("img").attr("class","video-image").attr("src","/surveillance/static/recorded_images/" + image_file).attr("width","320").attr("height",'180');
                    e1.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")
                    e2.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")
                    e3.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")
                    e4.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")
                    e5.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")
                    e5.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")
                    e6.attr("onclick","playVideo('/surveillance/static/recorded_videos/" + element['filename'] +"')")
                    
                })
                
            } else {
                video_list.append("div").attr("class","video-list-content").text(" ")
            }
        }
        

    } 

    
}

/// Update global parameters.
function updateParameters(year, month, day) {
    param_year = year;
    param_month = month;
    param_dom = day;
    curr_hour = 0;
    // console.log("Updated Params: " + param_year );
    // console.log("Updated Params: " + param_month );
    // console.log("Updated Params: " + param_dom );
    refreshCalendar();

}

// Function to play video by updating the <video> tag's source and forcing a play.
function playVideo(filename) {
    var vid = document.getElementById("video_play_area");
    vid.src = filename;
    vid.play();
    console.log(filename)
}

// this function is intentionally left blank.
function updateHour(hour) {

}
