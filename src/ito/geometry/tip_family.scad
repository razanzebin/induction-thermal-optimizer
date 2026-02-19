// tip_family.scad
// Units: mm. One file that can generate multiple tip families.

// ----- parameters passed via -D -----
shape = is_undef(shape) ? "solid_cone" : shape;
// Common
L = is_undef(L) ? 12 : L;
D = is_undef(D) ? 3  : D;     // outer diameter
$fn = is_undef($fn) ? 96 : $fn;

// For hollows / bluntness
wall = is_undef(wall) ? 0.4 : wall;     // wall thickness for hollow cone
tipR = is_undef(tipR) ? 0.6 : tipR;      // tip radius for blunt cone

// For ellipsoid
a = is_undef(a) ? (D/2) : a;  // semi-axis x
b = is_undef(b) ? (D/2) : b;  // semi-axis y
c = is_undef(c) ? (L)   : c;  // semi-axis z (height)

// ----- helpers -----
module solid_cone(L, D){
    cylinder(h=L, r1=D/2, r2=0.05);
}

module hollow_cone(L, D, wall){
    // Outer frustum (flat top) minus inner frustum
    // Keep a small top radius so subtraction doesn't create degeneracy
    r1o = D/2;
    r2o = max(0.3, 0.25*r1o);
    r1i = max(0.01, r1o - wall);
    r2i = max(0.01, r2o - wall);

    difference(){
        cylinder(h=L, r1=r1o, r2=r2o);
        translate([0,0,wall]) cylinder(h=max(0.01, L-wall), r1=r1i, r2=r2i);
    }
}

module rod(L, D){
    cylinder(h=L, r=D/2);
}

module hemisphere(D){
    r = D/2;
    intersection(){
        sphere(r=r);
        translate([-2*r,-2*r,0]) cube([4*r,4*r,2*r]);
    }
}

module half_ellipsoid(a,b,c){
    // Scale a sphere to ellipsoid then cut in half (z>=0)
    intersection(){
        scale([a,b,c]) sphere(r=1);
        translate([-2*a,-2*b,0]) cube([4*a,4*b,2*c]);
    }
}

module blunt_cone(L, D, tipR){
    // Rounded/blunt cone using Minkowski sum
    // NOTE: OpenSCAD cannot assign geometry to a variable; must inline primitives.
    minkowski(){
        cylinder(h=max(0.01, L-tipR), r1=D/2, r2=max(0.05, tipR));
        sphere(r=tipR);
    }
}

// ----- main switch -----
if (shape == "solid_cone")
    solid_cone(L,D);
else if (shape == "hollow_cone")
    hollow_cone(L,D,wall);
else if (shape == "rod")
    rod(L,D);
else if (shape == "hemisphere")
    hemisphere(D);
else if (shape == "half_ellipsoid")
    half_ellipsoid(a,b,c);
else if (shape == "blunt_cone")
    blunt_cone(L,D,tipR);
else
    solid_cone(L,D); // fallback
