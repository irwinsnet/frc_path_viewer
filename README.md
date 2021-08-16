# FRC Path Viewer
The *FRC Path Viewer* is a visualization tool for the FIRST Robotics Competition
(FRC) position tracking data that is generated during competitions. You can try
out the viewer at [http://pviewer.herokuapp.com](http://pviewer.herokuapp.com).

FIRST stands ***F**or **I**nspiration and **R**ecognition in **S**cience and
**T**echnology. FIRST uses robotics competitions to get young people excited
about science and technology. There are FIRST programs for elementary, middle,
and high school students. You can learn more about FIRST at
[firstinspires.org](http://firstinspires.org).

The tracking system that made this possible was provided by Zebra. 
[This blog post](https://www.zebra.com/us/en/blog/posts/2020/enabling-first-robotics-students-to-explore-their-edge.html)
provides additional information.

The viewer was written in Python using the [Bokeh]("https://docs.bokeh.org/)
package. It currently contains data for only two competitions, the 2020
Pacific Northwest District competitions at Glacier Peak High School in
Snohomish, WA and at West Valley High School in Spokane, WA. I expect to add
data for more competitions and add more features in the future.

The data was all downloaded from
[The Blue Alliance](https://www.thebluealliance.com/) using their
[Read API v3](https://www.thebluealliance.com/apidocs). I used custom
python code to download and process the information. The code is located
[in my zebra_motion Github repository](https://github.com/irwinsnet/zebra_motion).
FYI, I have not yet finished, documented, or cleaned up the code in the
*zebra_motion* repository. The code in that repository is subject to change.