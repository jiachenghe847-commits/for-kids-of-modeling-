// Double-precision C++17 implementation of rollout_kernel.py.
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace py = pybind11;
using P = std::array<double,2>;
using Poly = std::vector<P>;
using World = std::array<double,6>;
using History = std::vector<std::tuple<double,double,std::string,double>>;
constexpr double pi = 3.14159265358979323846;
double dist(P a,P b) { return std::hypot(a[0]-b[0],a[1]-b[1]); }
double rank_distance(double value) { return std::floor(value*1e7+.5); }
double dot(P a,P b) { return a[0]*b[0]+a[1]*b[1]; }
P add(P a,P b) { return {a[0]+b[0],a[1]+b[1]}; }
P sub(P a,P b) { return {a[0]-b[0],a[1]-b[1]}; }
P mul(P a,double t) { return {a[0]*t,a[1]*t}; }

Poly clip_poly(Poly poly,const Poly& normals,const std::vector<double>& limits) {
    for(size_t i=0;i<normals.size();++i) {
        if(poly.empty()) break;
        Poly out; P previous=poly.back(); double vp=dot(normals[i],previous)-limits[i];
        for(P current:poly) {
            double vc=dot(normals[i],current)-limits[i];
            if((vc<=1e-8)!=(vp<=1e-8) && std::abs(vp-vc)>1e-15)
                out.push_back(add(previous,mul(sub(current,previous),vp/(vp-vc))));
            if(vc<=1e-8) out.push_back(current);
            previous=current; vp=vc;
        }
        poly.clear();
        for(P point:out) if(poly.empty() || dist(point,poly.back())>1e-8) poly.push_back(point);
        if(poly.size()>1 && dist(poly.front(),poly.back())<1e-8) poly.pop_back();
    }
    return poly;
}

Poly observe(Poly poly,P point,double angle) {
    double low=(angle-1.005)*pi/180,high=(angle+1.005)*pi/180;
    Poly ns={{std::sin(low),-std::cos(low)},{-std::sin(high),std::cos(high)}};
    poly=clip_poly(poly,ns,{dot(ns[0],point),dot(ns[1],point)});
    if(std::any_of(poly.begin(),poly.end(),[&](P x){return dist(x,point)>1500;})) {
        ns.clear();std::vector<double> limits;
        for(int k=0;k<64;++k) {
            P n={std::cos(k*2*pi/64),std::sin(k*2*pi/64)};
            ns.push_back(n);limits.push_back(1500+dot(n,point));
        }
        poly=clip_poly(poly,ns,limits);
    }
    if(poly.empty()) throw std::runtime_error("Empty hypothetical intersection; historical constraints retained");
    return poly;
}

std::pair<P,double> circle(const Poly& poly) {
    if(poly.empty()) throw std::runtime_error("Empty feasible region");
    P center=poly[0];double radius=0;
    for(size_t i=0;i<poly.size();++i) {
        P a=poly[i];if(dist(a,center)<=radius+1e-9) continue;
        center=a;radius=0;
        for(size_t j=0;j<i;++j) {
            P b=poly[j];if(dist(b,center)<=radius+1e-9) continue;
            center=mul(add(a,b),.5);radius=dist(a,b)/2;
            for(size_t k=0;k<j;++k) {
                P c=poly[k];if(dist(c,center)<=radius+1e-9) continue;
                double bx=b[0]-a[0],by=b[1]-a[1],cx=c[0]-a[0],cy=c[1]-a[1];
                double det=2*(bx*cy-by*cx);
                if(std::abs(det)<1e-12) {
                    std::array<std::pair<P,P>,3> pairs={{{a,b},{a,c},{b,c}}};
                    auto pair=*std::max_element(pairs.begin(),pairs.end(),[](auto u,auto v){return dist(u.first,u.second)<dist(v.first,v.second);});
                    center=mul(add(pair.first,pair.second),.5);
                } else {
                    double bb=bx*bx+by*by,cc=cx*cx+cy*cy;
                    center={a[0]+(cy*bb-by*cc)/det,a[1]+(bx*cc-cx*bb)/det};
                }
                radius=dist(a,center);
            }
        }
    }
    radius=0;for(P p:poly) radius=std::max(radius,dist(p,center));
    return {center,radius};
}

struct Config {
    double trigger,spacing;bool shift,small;
    explicit Config(const py::dict& d):trigger(d["optical_trigger"].cast<double>()),
        spacing(d["spacing"].cast<double>()),shift(d["safe_shift"].cast<bool>()),small(d["small_cover"].cast<bool>()) {}
};

P safe_center(const Poly& poly,P center,P start,std::optional<P> next,bool enabled) {
    if(!enabled) return center;
    P target=next ? mul(add(start,*next),.5):start;
    double lo=0,hi=1;
    for(int i=0;i<32;++i) {
        double t=(lo+hi)/2;P p=add(center,mul(sub(target,center),t));
        bool good=std::all_of(poly.begin(),poly.end(),[&](P x){return dist(p,x)<=19.8;});
        if(good) lo=t;else hi=t;
    }
    return add(center,mul(sub(target,center),lo));
}

Poly optical(const Poly& poly,double bearing,double spacing,bool small) {
    auto [center,radius]=circle(poly);
    if(radius<=19.8) return {center};
    if(small && radius<=39.6) {
        Poly points;bool good=true;
        for(int k=0;k<6;++k) {
            double low=k*pi/3,high=(k+1)*pi/3;
            Poly ns={{std::sin(low),-std::cos(low)},{-std::sin(high),std::cos(high)}};
            Poly part=clip_poly(poly,ns,{dot(ns[0],center),dot(ns[1],center)});
            if(!part.empty()) {
                auto [c,r]=circle(part);if(r>19.8) {good=false;break;}
                points.push_back(c);
            }
        }
        if(good) return points;
    }
    double co=std::cos(bearing*pi/180),si=std::sin(bearing*pi/180);
    Poly local;for(auto [x,y]:poly) local.push_back({co*x+si*y,-si*x+co*y});
    P lo=local[0],hi=local[0];for(P p:local) for(int k=0;k<2;++k) {lo[k]=std::min(lo[k],p[k]);hi[k]=std::max(hi[k],p[k]);}
    Poly points;
    for(int i=int(std::floor(lo[0]/spacing));i<=int(std::floor(hi[0]/spacing));++i)
        for(int j=int(std::floor(lo[1]/spacing));j<=int(std::floor(hi[1]/spacing));++j) {
            Poly part=clip_poly(local,{{1,0},{-1,0},{0,1},{0,-1}},
                                {(i+1)*spacing,-i*spacing,(j+1)*spacing,-j*spacing});
            if(!part.empty()) {double x=(i+.5)*spacing,y=(j+.5)*spacing;points.push_back({co*x-si*y,si*x+co*y});}
        }
    return points;
}

std::pair<std::string,P> fixed(const Poly& poly,P start,double bearing,P received,
                              const Poly& used,const Poly& failed,int rounds,std::optional<P> next,const Config& cfg) {
    auto [center,radius]=circle(poly);
    if(radius<=19.8) return {"certified_clear",safe_center(poly,center,start,next,cfg.shift)};
    if(radius<=cfg.trigger || rounds>=12) {
        Poly points=optical(poly,bearing,cfg.spacing,cfg.small),fresh;
        for(P p:points) if(std::all_of(failed.begin(),failed.end(),[&](P f){return dist(p,f)>1e-7;})) fresh.push_back(p);
        if(fresh.empty()) throw std::runtime_error("Exhaustive optical covering failed");
        return {"optical",*std::min_element(fresh.begin(),fresh.end(),[&](P a,P b){return rank_distance(dist(a,start))<rank_distance(dist(b,start));})};
    }
    double angle=bearing*pi/180;P direction={std::cos(angle),std::sin(angle)},side={-std::sin(angle),std::cos(angle)};
    double advance=std::max(0.,dot(sub(center,received),direction));
    P base=add(received,mul(direction,advance));
    Poly choices={add(base,mul(side,-20)),add(base,mul(side,20))},fresh;
    for(P p:choices) if(std::all_of(used.begin(),used.end(),[&](P u){return dist(p,u)>1;})) fresh.push_back(p);
    if(fresh.empty()) {double step=20*(1+rounds);fresh={add(base,mul(side,step)),add(base,mul(side,-step))};}
    return {"probe",*std::min_element(fresh.begin(),fresh.end(),[&](P a,P b){return rank_distance(dist(start,a)+dist(a,center))<rank_distance(dist(start,b)+dist(b,center));})};
}

std::string key(P p) {
    char buffer[128];std::snprintf(buffer,sizeof(buffer),"%.8f|%.8f",p[0],p[1]);return buffer;
}

py::object evaluate(const Poly& poly,P start,int tuned_channel,int channel,double bearing,P received,
                    const History& history,const Poly& failed,int rounds,const std::vector<World>& worlds,
                    const std::string& action,P point,std::optional<P> next,const py::dict& config,double deadline) {
    Config cfg(config);
    // Python's monotonic clock epoch is platform-specific (not steady_clock's).
    double remaining=deadline-py::module_::import("time").attr("monotonic")().cast<double>();
    auto finish=std::chrono::steady_clock::now()+std::chrono::duration<double>(std::max(0.,remaining));
    bool interrupted=false;double total=0,maximum=0;std::array<double,5> components{};
    {
        py::gil_scoped_release release;
        auto expired=[&](){return std::chrono::steady_clock::now()>=finish;};
        for(const World& world:worlds) {
            if(expired()) {interrupted=true;break;}
            P source={world[0],world[1]},current=start,last_received=received;
            Poly region=poly,used,misses=failed;
            double last_bearing=bearing;int probes=rounds,tuned=tuned_channel;
            std::map<std::string,std::pair<std::string,double>> memory;
            for(auto [x,y,kind,angle]:history) {P p={x,y};memory[key(p)]={kind,angle};used.push_back(p);}
            std::string kind=action;P destination=point;std::array<double,5> cost{};
            std::optional<Poly> optical_points;
            while(true) {
                if(expired()) {interrupted=true;break;}
                cost[0]+=dist(current,destination)/5;current=destination;
                if(kind!="probe") {
                    if(dist(current,source)<=20+1e-9) {cost[4]+=5;break;}
                    if(kind=="certified_clear") throw std::runtime_error("Hypothesis outside certified clear");
                    cost[3]+=3;misses.push_back(current);
                    if(circle(region).second<=cfg.trigger || probes>=12) {
                        Poly fresh;
                        if(!optical_points) {
                            for(P p:optical(region,last_bearing,cfg.spacing,cfg.small))
                                if(std::all_of(misses.begin(),misses.end(),[&](P f){return dist(p,f)>1e-7;})) fresh.push_back(p);
                        } else for(P p:*optical_points) if(dist(p,current)>1e-7) fresh.push_back(p);
                        optical_points=fresh;
                        if(fresh.empty()) throw std::runtime_error("Exhaustive optical covering failed");
                        kind="optical";
                        destination=*std::min_element(fresh.begin(),fresh.end(),[&](P a,P b){return rank_distance(dist(a,current))<rank_distance(dist(b,current));});
                        continue;
                    }
                } else {
                    cost[1]+=5;cost[2]+=(tuned!=channel);tuned=channel;++probes;used.push_back(current);
                    std::string position_key=key(current),response;double angle;
                    auto it=memory.find(position_key);
                    if(it!=memory.end()) {response=it->second.first;angle=it->second.second;}
                    else {
                        bool visible=(current[0]-source[0])*world[3]+(current[1]-source[1])*world[4]>=-1e-9 && dist(current,source)<=world[2]+1e-9;
                        response=visible ? (dist(current,source)<=5 ? "near":"direction"):"no_signal";
                        angle=std::fmod(std::atan2(source[1]-current[1],source[0]-current[0])*180/pi+world[5],360.);
                        if(angle<0) angle+=360;
                        memory[position_key]={response,angle};
                    }
                    if(response=="near") {cost[4]+=5;break;}
                    if(response=="direction") {region=observe(region,current,angle);last_received=current;last_bearing=angle;optical_points.reset();}
                }
                std::tie(kind,destination)=fixed(region,current,last_bearing,last_received,used,misses,probes,next,cfg);
            }
            if(interrupted) break;
            if(next) cost[0]+=dist(current,*next)/5;
            double sum=0;for(size_t i=0;i<5;++i) {components[i]+=cost[i];sum+=cost[i];}
            total+=sum;maximum=std::max(maximum,sum);
        }
    }
    if(interrupted) return py::none();
    if(worlds.empty()) throw std::runtime_error("No compatible sampled worlds");
    for(double& component:components) component/=worlds.size();
    py::dict result;result["mean_s"]=total/worlds.size();result["max_s"]=maximum;
    result["worlds"]=worlds.size();result["components_s"]=components;return result;
}

PYBIND11_MODULE(_rollout_cpp,m) {
    m.def("evaluate",&evaluate);
    m.def("circle",&circle);
    m.def("clip_polygon",&clip_poly);
    m.def("observe_polygon",&observe);
    m.def("optical",&optical);
    m.def("fixed_action",[](const Poly& poly,P start,double bearing,P received,const Poly& used,const Poly& failed,
                             int rounds,std::optional<P> next,const py::dict& cfg){return fixed(poly,start,bearing,received,used,failed,rounds,next,Config(cfg));});
    m.attr("precision")="double";
    m.attr("fast_math")=false;
    m.attr("source_sha256")=ROLLOUT_SOURCE_SHA256;
}
